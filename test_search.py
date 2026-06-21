# test_search.py
from ddgs import DDGS


def verification_search(query):
    print(f"\n📡 Requesting data stream via modern DDGS for: '{query}'")
    try:
        # Initialize the updated metasearch client
        client = DDGS()

        # We explicitly query the API/Lite backend matrix to dodge IP blocks
        results = client.text(query, max_results=3)

        if not results:
            return "⚠️ EMPTY: Connected successfully, but search backends returned an empty index."

        formatted_results = []
        for index, item in enumerate(results, 1):
            title = item.get("title", "No Title")
            # The library updated the snippet key from 'body' to 'body' or 'snippet'
            snippet = item.get("body", item.get("snippet", "No Text Body"))
            formatted_results.append(f"Result {index}: [{title}]\n👉 {snippet}")

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"❌ EXCEPTION CAUGHT: {str(e)}"


def run_diagnostic():
    print("=" * 60)
    print("🚀 RUNNING COMPATIBILITY-LAYER DDGS VERIFICATION TEST")
    print("=" * 60)

    # Test Query
    query = "what is the gold price today in all districts of west bengal?"
    result = verification_search(query)

    print("-" * 40)
    print("RESULT OUTPUT:")
    print(result)
    print("-" * 40)


if __name__ == "__main__":
    run_diagnostic()
