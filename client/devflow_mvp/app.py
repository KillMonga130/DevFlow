import json
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, Button, RichLog, Static
from textual import on
from textual.screen import Screen

from .ollama_client import generate_code_exercise, get_feedback
from .widgets import CodeEditor, ProgressTracker

class DevFlowApp(App):
    """DevFlow: An AI-powered code review and exercise app."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_exercise", "New Exercise"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_exercise = ""
        self.current_solution = ""
        self.score = 0
        self.total_exercises = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="main_container"):
            with Vertical(id="exercise_panel"):
                yield Static("🎯 [bold]Code Exercise[/bold]", classes="panel-title")
                yield RichLog(id="exercise_display", auto_scroll=False)
            
            with Vertical(id="editor_panel"):
                yield Static("✏️ [bold]Your Code Review[/bold]", classes="panel-title")
                yield CodeEditor(language="python", id="code_editor")
                yield Button("📤 Submit Review", id="submit_button", variant="primary")
            
            with Vertical(id="feedback_panel"):
                yield Static("💡 [bold]AI Feedback[/bold]", classes="panel-title")
                yield RichLog(id="feedback_display", auto_scroll=True)
            
            with Vertical(id="metrics_panel"):
                yield Static("📊 [bold]Your Progress[/bold]", classes="panel-title")
                yield ProgressTracker(id="progress_tracker")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.load_progress()
        self.run_worker(self.action_new_exercise(), name="generate_exercise")

    def load_progress(self) -> None:
        """Load progress from a file."""
        try:
            with open("progress_db.json", "r") as f:
                data = json.load(f)
                self.score = data.get("score", 0)
                self.total_exercises = data.get("total_exercises", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            self.score = 0
            self.total_exercises = 0
        
        tracker = self.query_one("#progress_tracker", ProgressTracker)
        tracker.update_progress(self.score, 10)

    def save_progress(self) -> None:
        """Save progress to a file."""
        try:
            with open("progress_db.json", "w") as f:
                json.dump({
                    "score": self.score,
                    "total_exercises": self.total_exercises
                }, f)
        except Exception as e:
            print(f"Error saving progress: {e}")

    def update_feedback(self, text: str) -> None:
        """Update the feedback panel."""
        feedback_display = self.query_one("#feedback_display", RichLog)
        feedback_display.clear()
        feedback_display.write(text)

    async def action_new_exercise(self) -> None:
        """Generate and display a new AI exercise."""
        exercise_display = self.query_one("#exercise_display", RichLog)
        exercise_display.clear()
        self.query_one("#code_editor").clear()
        
        self.update_feedback("Generating new exercise...")
        
        try:
            exercise = await generate_code_exercise("Python bug fixing")
            self.current_solution = exercise
            exercise_display.write(exercise)
            self.update_feedback("Exercise loaded! Review the code and submit your analysis.")
        except Exception as e:
            self.update_feedback(f"Error generating exercise: {str(e)}")

    @on(Button.Pressed, "#submit_button")
    async def handle_submit(self, event: Button.Pressed) -> None:
        """Handle the user's code review submission."""
        editor = self.query_one("#code_editor", CodeEditor)
        user_review = editor.text

        if not user_review:
            self.update_feedback("❌ Please write your code review before submitting.")
            return

        self.update_feedback("🔄 Analyzing your review...")
        
        try:
            feedback = await get_feedback(user_review, self.current_solution)
            self.score += 1  # Increment score
            self.total_exercises += 1
            self.save_progress()
            
            # Update progress tracker
            tracker = self.query_one("#progress_tracker", ProgressTracker)
            tracker.update_progress(self.score, 10)
            
            self.update_feedback(f"✅ {feedback}")
        except Exception as e:
            self.update_feedback(f"❌ Error processing review: {str(e)}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle any button press events."""
        button_id = event.button.id
        if button_id == "submit_button":
            # Pass the event to handle_submit
            self.run_worker(self.handle_submit(event), name="submit_review")

if __name__ == "__main__":
    app = DevFlowApp()
    app.run()