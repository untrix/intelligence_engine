# Mock Data for sample workflows

Bundled files for trying the **Job Candidate Review** and **Submit Candidate Review (Needs MCP Key)** sample workflows without preparing your own folders.

## Layout

| Path | Purpose |
|------|---------|
| `Job Files/` | Job description, interview template, and questionnaire (`.docx`) for the role |
| `Jon Stewart/` | Example candidate folder for the quick start (may be empty — add a resume to test file reads) |
| `John Stuart/` | Alternate example folder |
| `Yoshua Benjio/` | Another example candidate folder |

## Running the sample

On the Workflows page, run either sample workflow with:

- `job_files` → `./docs/Mock Data/Job Files`
- `candidate_files` → `./docs/Mock Data/Jon Stewart` (or another candidate folder)
- `candidate_name` → any label, e.g. `Jon Stewart`

The agent uses `read_local_folder` / `read_local_path` for these directory variables. Paths are resolved from the app home directory (project root by default).
