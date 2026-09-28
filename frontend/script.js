// ========================================
// MARKET LENS BACKEND
// ========================================

// Replace this with your Render backend URL.

const BACKEND_URL = "https://market-lens-wn6l.onrender.com";


// ========================================
// SET EXAMPLE QUERY
// ========================================

function setQuery(text) {

    const queryBox = document.getElementById("query");

    queryBox.value = text;

    queryBox.focus();
}


// ========================================
// ASK MARKET LENS
// ========================================

async function askMarketLens() {

    const queryBox = document.getElementById("query");

    const answerBox = document.getElementById("answer");

    const askButton = document.getElementById("askButton");


    const query = queryBox.value.trim();


    // Check empty query

    if (!query) {

        answerBox.className = "error";

        answerBox.textContent =
            "Please enter a question.";

        return;
    }


    // Loading state

    askButton.disabled = true;

    askButton.textContent = "Thinking...";


    answerBox.className = "loading";

    answerBox.textContent =
        "Market Lens is processing your question...";


    try {

        const response = await fetch(
            `${BACKEND_URL}/query`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    query: query
                })
            }
        );


        // Check HTTP response

        if (!response.ok) {

            throw new Error(
                `HTTP error: ${response.status}`
            );
        }


        // Convert response to JSON

        const data = await response.json();


        console.log("Backend response:", data);


        /*
            Expected backend response:

            {
                "answer": "..."
            }

            If your backend uses another
            field, we can change this.
        */

        const answer =
            data.answer ||
            data.response ||
            data.result ||
            JSON.stringify(data);


        // Display answer

        answerBox.className = "answer";

        answerBox.textContent = answer;


    } catch (error) {

        console.error("Market Lens error:", error);


        answerBox.className = "error";

        answerBox.textContent =
            "Unable to connect to Market Lens backend. " +
            "Please check the backend URL and try again.";


    } finally {

        // Restore button

        askButton.disabled = false;

        askButton.textContent = "Ask Market Lens";

    }
}


// ========================================
// CTRL + ENTER
// ========================================

document
    .getElementById("query")
    .addEventListener("keydown", function(event) {

        if (event.ctrlKey && event.key === "Enter") {

            askMarketLens();

        }

    });