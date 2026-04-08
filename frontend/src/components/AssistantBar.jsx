import React from 'react';

const AssistantBar = () => {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-2xl z-40 px-6">
      <div className="glass rounded-[2rem] p-2 pl-6 flex items-center gap-4 border border-white/10 shadow-2xl shadow-indigo-900/20 backdrop-blur-2xl bg-slate-950/40">
        <i className="fas fa-sparkles text-indigo-400 text-lg"></i>
        <input
          type="text"
          placeholder="Ask assistant to search or analyze data..."
          className="bg-transparent border-none outline-none text-slate-100 w-full placeholder-slate-400 text-base py-3 font-medium"
        />
        <button className="bg-indigo-600 hover:bg-indigo-500 text-white w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-105 shrink-0 shadow-lg shadow-indigo-600/30">
          <i className="fas fa-arrow-up text-lg"></i>
        </button>
      </div>
    </div>
  );
};

export default AssistantBar;