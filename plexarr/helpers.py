from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Header, Select, Button, Input, Label


###############################################################################
#             CLI GUI APP - Select Option from a List of Choices!             #
###############################################################################
class SelectApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    Label {
        align: center middle;
        content-align-horizontal: center;
        content-align-vertical: middle;
        border: solid green;
    }
    Select {
        width: 46;
    }
    Button {
        align: center middle;
        content-align-horizontal: center;
        content-align-vertical: middle;
    }
    """

    def __init__(self, header: str="Teddy's App Selector!", placeholder: str="Please Select an App", apps: list=[]) -> None:
        self.HEADER = header
        self.PLACEHOLDER = placeholder
        self.APPS = apps
        self.INDEXES = {a: i for i, a in enumerate(apps)}
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        # yield Label('Failed to Find the Artist "' + self.ARTIST_NAME + '" in Plex...')
        yield Label(self.HEADER)
        yield Select.from_values(self.APPS, prompt=self.PLACEHOLDER)
        yield Button("Submit", id="submit", variant="success", disabled=True)

    def on_mount(self) -> None:
        self.title = ""

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        self.APP = str(event.value)
        self.INDEX = self.INDEXES[self.APP]
        self.query_one(Button).disabled = False

    @on(Button.Pressed)
    def button_pressed(self, event: Button.Pressed):
        self.exit((self.APP, self.INDEX))


def SelectOption(header="", placeholder="", apps=[]):
    return SelectApp(header=header, placeholder=placeholder, apps=apps).run()


# Option Selector Test ############################################################################
"""
from plexarr.plex_api improt PlexPy

p = PlexPy()

selected_library, index = SelectOption(header="PMS Library & Partial Scanner", placeholder="Please Select a Library", apps=[s.title for s in p.library.sections()])
print(f'Selected Library: {selected_library}, index = {index}')

library = p.library.section(title=selected_library)
library.update(path="/Volumes/plex4/series8/Married at First Sight/Season 01")
"""


###############################################################################
#                           CLI GUI APP - INPUT APP                           #
###############################################################################
class InputApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    Input {
        margin: 1 1;
    }
    Label {
        margin: 1 2;
    }
    Button {
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        self.first_name = ""
        self.last_name = ""
        yield Label("Please enter the artist name as it appears in Plex")
        yield Input(placeholder="Artist Name", name="artist_name")
        yield Button("Submit", id="submit", variant="success", disabled=True)

    @on(Input.Changed)
    def input_changed(self, event: Input.Changed) -> None:
        self.artist_name = event.input.value
        self.query_one(Button).disabled = False

    @on(Button.Pressed)
    def button_pressed(self, event: Button.Pressed):
        self.exit(self.artist_name)


def InputArtist():
    return InputApp().run()
