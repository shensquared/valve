# Valve

A visual class schedule planner for MIT. Built for planning lectures, labs, recitations, and midterms across the semester.

Pre-configured with MIT Registrar key dates. The JSON-based semester data makes it adaptable for other institutions.

Why the name? [Hydrant](https://hydrant.mit.edu) helps students pick classes. Valve helps instructors plan them.

## Features

- **Visual Calendar**: Week-by-week semester view with color-coded events
- **Event Types**: Toggle lectures, labs, and recitations by day of the week
- **Midterm Placement**: Drag-and-drop midterms onto specific dates
- **Lecture Topics**: Manage and reorder topics via drag-and-drop or paste from a list
- **Academic Calendar**: Automatically handles holidays, breaks, and finals periods
- **Save/Load**: Export and import configurations as JSON
- [ ] List view
- [ ] iCal/Google Calendar export
- [ ] Canvas/CAT-SOOP sync
- [ ] Section-based alternative scheduling

## Usage

1. Go to [shenshen.mit.edu/valve](https://shenshen.mit.edu/valve/)
2. Select a semester from the dropdown
3. Choose which days your class meets for each event type
4. Drag midterms to their dates
5. Add lecture topics in the sidebar
6. Save your configuration

## Project Structure

```
valve/
├── index.html          # Main page
├── app.js              # Application logic
├── styles.css          # Styling
├── semesters/          # Semester configurations (JSON)
├── theme/              # Branding assets
└── verifiers/          # Python validation scripts
```

## Tech Stack

Vanilla HTML/CSS/JavaScript with no dependencies. Python scripts for data validation.

The "Last Updated" footer is automatically set by a git pre-commit hook.

## Development Setup

To set up the pre-commit hooks (auto-updates the "Last Updated" date):

```bash
# Install pre-commit (one-time)
brew install pre-commit  # macOS
# or: pip install pre-commit  # other platforms

# Install the hooks (one-time per clone)
pre-commit install
```
