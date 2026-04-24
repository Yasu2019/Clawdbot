import openai
import os

# LiteLLM proxy settings
client = openai.OpenAI(
    api_key="local-dev-key",
    base_url="http://localhost:4000/v1"
)

def test_kimi():
    print("Connecting to Kimi (via LiteLLM)...")
    try:
        response = client.chat.completions.create(
            model="kimi-agent-primary",
            messages=[{"role": "user", "content": "Ping. Are you Kimi K2.6?"}],
            max_tokens=50
        )
        print("\nSuccess! Kimi responded:")
        print(f"---")
        print(response.choices[0].message.content)
        print(f"---")
    except Exception as e:
        print(f"\nFailed to connect to Kimi: {e}")

if __name__ == "__main__":
    test_kimi()
