from agent import run_agent

def main():
    print("MCP CLI Test (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        try:
            response, sql = run_agent(user_input)
            if sql:
                print(f"SQL: {sql}\n")
            print(f"Bot: {response}\n")
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()