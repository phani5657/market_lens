// ========================================
// MARKET LENS BACKEND
// ========================================

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


        console.log("Response status:", response.status);


        // Check HTTP response

        if (!response.ok) {

            throw new Error(
                `Backend returned ${response.status}`
            );
        }


        // Backend returns plain text/string

        const answer = await response.text();


        console.log("Backend answer:", answer);


        // Display answer

        answerBox.className = "answer";

        answerBox.textContent = answer;


    } catch (error) {

        console.error("Market Lens error:", error);


        answerBox.className = "error";

        answerBox.textContent =
            "Unable to get a response from Market Lens.\n\n" +
            error.message;


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