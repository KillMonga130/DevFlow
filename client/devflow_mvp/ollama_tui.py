import ollama
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Input, Static, TextArea # Corrected import

class OllamaTUI(App):
    """A Textual app to chat with a local Ollama model."""

    CSS_PATH = "styles.tcss"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(
            Static("Your Message:"),
            Input(placeholder="Type your message here...", id="user_input"),
            Static("Ollama's Response:"),
            TextArea(id="response_area", read_only=True),
        )
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_message = event.value
        self.query_one("#user_input", Input).value = ""
        self.query_one("#response_area", TextArea).load_text(f"User: {user_message}\n")

        # Call the Ollama model
        try:
            stream = ollama.chat(
                model="devflow-gpt-fast:latest",  # Replace with the model you use (e.g., llama3, mistral)
                messages=[{'role': 'user', 'content': user_message}],
                stream=True,
            )
            response_text = ""
            for chunk in stream:
                if 'content' in chunk['message']:
                    response_text += chunk['message']['content']
                    self.query_one("#response_area", TextArea).load_text(
                        self.query_one("#response_area", TextArea).text + chunk['message']['content']
                    )
        except Exception as e:
            self.query_one("#response_area", TextArea).load_text(f"Error: {e}")

if __name__ == "__main__":
    app = OllamaTUI()
    app.run()