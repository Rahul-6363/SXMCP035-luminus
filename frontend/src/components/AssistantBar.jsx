import { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react';
import { BACKEND_URL, MAILER_URL, VENDOR_EMAIL } from '../utils/constants';

const sessionId = crypto.randomUUID();

const AssistantBar = forwardRef(({ onActionComplete }, ref) => {
  const [input, setInput]       = useState('');
  const [messages, setMessages] = useState([]);  // [{role, content, shortages}]
  const [loading, setLoading]   = useState(false);
  const [open, setOpen]         = useState(false);
  const threadRef               = useRef(null);

  // Scroll to bottom when new message arrives
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages]);

  const addMessage = (role, content, shortages = []) => {
    setMessages(prev => [...prev, { role, content, shortages }]);
  };

  const doSubmit = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setOpen(true);
    setInput('');
    addMessage('user', trimmed);
    setLoading(true);

    // Add an empty assistant message that we'll fill in as tokens arrive
    setMessages(prev => [...prev, { role: 'assistant', content: '', shortages: [], _streaming: true }]);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 180000); // 3 min timeout

    const updateLast = (updater) =>
      setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, ...updater(m) } : m));

    try {
      const res = await fetch(`${BACKEND_URL}/chat/stream`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ text: trimmed, session_id: sessionId }),
        signal:  controller.signal,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        updateLast(() => ({ content: `Error ${res.status}: ${data.detail ?? 'Backend error.'}`, _streaming: false }));
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let seenToken = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE: events separated by double newline
        const parts = buffer.split('\n\n');
        buffer = parts.pop(); // keep incomplete chunk

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data: ')) continue;
          let event;
          try { event = JSON.parse(line.slice(6)); } catch { continue; }

          if (event.type === 'status') {
            if (!seenToken) {
              updateLast(() => ({ content: event.text, _status: true, _tool: null }));
            }
          } else if (event.type === 'tool') {
            // MCP tool routing badge — visible to judges
            updateLast(() => ({
              content:  '',
              _status:  false,
              _tool:    { name: event.name, label: event.label, icon: event.icon, color: event.color },
            }));
          } else if (event.type === 'token') {
            if (!seenToken) {
              seenToken = true;
              updateLast(() => ({ content: event.text, _status: false }));
            } else {
              updateLast(m => ({ content: m.content + event.text }));
            }
          } else if (event.type === 'done') {
            updateLast(() => ({ shortages: event.shortages ?? [], _streaming: false, _status: false }));
            if (onActionComplete) onActionComplete();
          } else if (event.type === 'error') {
            updateLast(() => ({ content: event.text, _streaming: false, _status: false, _tool: null }));
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        updateLast(() => ({ content: 'Request timed out — the LLM took too long. Try a simpler question or check if Ollama is running.', _streaming: false }));
      } else {
        updateLast(() => ({ content: 'Could not reach backend. Is it running on port 8000?', _streaming: false }));
      }
    } finally {
      clearTimeout(timeout);
      setLoading(false);
      // Ensure _streaming flag is cleared
      setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, _streaming: false } : m));
    }
  };

  // Exposed so BomSection can pre-fill and submit
  useImperativeHandle(ref, () => ({
    submitText: (text) => { setInput(text); doSubmit(text); },
  }));

  const sendOrderEmail = async (shortages, msgIndex) => {
    try {
      const res  = await fetch(`${MAILER_URL}/send-vendor-email`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ shortages, vendor_email: VENDOR_EMAIL }),
      });
      const data = await res.json();
      // Clear shortages from that message, append confirmation
      setMessages(prev => prev.map((m, i) =>
        i === msgIndex ? { ...m, shortages: [], content: m.content + `\n\n✓ ${data.message ?? 'Order email sent.'}` } : m
      ));
    } catch {
      addMessage('assistant', 'Failed to send email — is the mailer running on port 3000?');
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-2xl z-40 px-6 flex flex-col gap-3">

      {/* Chat thread */}
      {open && (
        <div
          ref={threadRef}
          className="glass rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl shadow-xl max-h-96 overflow-y-auto flex flex-col gap-3 p-4"
        >
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-slate-800 text-slate-200 rounded-bl-sm'
              }`}>
                {/* MCP Tool badge — shown before the response so judges see tool routing */}
                {msg._tool && (
                  <div className={`flex items-center gap-2 mb-2 px-2 py-1 rounded-lg text-xs font-semibold w-fit
                    ${msg._tool.color === 'indigo'  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/25' :
                      msg._tool.color === 'emerald' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/25' :
                      msg._tool.color === 'cyan'    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/25' :
                      msg._tool.color === 'violet'  ? 'bg-violet-500/15 text-violet-300 border border-violet-500/25' :
                      msg._tool.color === 'green'   ? 'bg-green-500/15 text-green-300 border border-green-500/25' :
                      msg._tool.color === 'amber'   ? 'bg-amber-500/15 text-amber-300 border border-amber-500/25' :
                      msg._tool.color === 'rose'    ? 'bg-rose-500/15 text-rose-300 border border-rose-500/25' :
                      msg._tool.color === 'teal'    ? 'bg-teal-500/15 text-teal-300 border border-teal-500/25' :
                                                      'bg-slate-700 text-slate-300 border border-slate-600'}`}>
                    <i className={`fas ${msg._tool.icon} text-xs`}></i>
                    <span className="opacity-60">MCP →</span>
                    <span>{msg._tool.label}</span>
                  </div>
                )}

                {msg._status
                  ? <span className="text-slate-400 italic text-xs">{msg.content}</span>
                  : msg.content
                }
                {msg._streaming && !msg._status && (
                  <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 align-middle animate-pulse" />
                )}

                {/* Shortage table */}
                {msg.shortages?.length > 0 && (
                  <div className="mt-3">
                    <p className="text-amber-400 font-semibold mb-2 text-xs">
                      {msg.shortages.length} item(s) short — order from vendor?
                    </p>
                    <table className="w-full text-xs mb-3 text-slate-300">
                      <thead>
                        <tr className="text-slate-400 border-b border-white/10">
                          <th className="text-left py-1">Item</th>
                          <th className="text-right py-1">Need</th>
                          <th className="text-right py-1">Have</th>
                          <th className="text-right py-1 text-rose-400">Short</th>
                        </tr>
                      </thead>
                      <tbody>
                        {msg.shortages.map(s => (
                          <tr key={s.item_code} className="border-b border-white/5">
                            <td className="py-1">
                              <span className="font-mono">{s.item_code}</span>
                              <br/>
                              <span className="text-slate-500">{s.description}</span>
                            </td>
                            <td className="text-right">{s.required} {s.uom}</td>
                            <td className="text-right">{s.available}</td>
                            <td className="text-right text-rose-400 font-bold">{s.shortage}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button
                      onClick={() => sendOrderEmail(msg.shortages, i)}
                      className="bg-amber-500 hover:bg-amber-400 text-slate-900 font-bold px-4 py-2 rounded-xl text-xs transition-all"
                    >
                      Yes, send order email to vendor
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && !messages.some(m => m._streaming) && (
            <div className="flex justify-start">
              <div className="bg-slate-800 text-slate-400 rounded-2xl rounded-bl-sm px-4 py-3 text-sm">
                <i className="fas fa-spinner fa-spin mr-2"></i>Connecting…
              </div>
            </div>
          )}
        </div>
      )}

      {/* Input bar */}
      <div className="glass rounded-[2rem] p-2 pl-6 flex items-center gap-4 border border-white/10 shadow-2xl shadow-indigo-900/20 backdrop-blur-2xl bg-slate-950/40">
        <i className="fas fa-sparkles text-indigo-400 text-lg"></i>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); doSubmit(input); } }}
          placeholder="Ask about inventory or BOM…"
          className="bg-transparent border-none outline-none text-slate-100 w-full placeholder-slate-400 text-base py-3 font-medium"
        />
        {messages.length > 0 && (
          <button
            onClick={() => { setMessages([]); setOpen(false); }}
            className="text-slate-500 hover:text-slate-300 text-sm px-2"
            title="Clear chat"
          >
            <i className="fas fa-trash-alt"></i>
          </button>
        )}
        <button
          onClick={() => doSubmit(input)}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-105 shrink-0 shadow-lg shadow-indigo-600/30"
        >
          <i className={`fas ${loading ? 'fa-spinner fa-spin' : 'fa-arrow-up'} text-lg`}></i>
        </button>
      </div>
    </div>
  );
});

AssistantBar.displayName = 'AssistantBar';
export default AssistantBar;
