# AI Agent Constraints & Token Saving Rules

## Token Economy
- **Do not read files blindly:** Never use`grep`,`find`, or bulk-read commands unless explicitly asked.
- **Targeted reads only:** Read a maximum of 2 files per turn. Ask for permission before reading more.
- **No media/binary files:** Never attempt to read or parse images, PDFs, or compiled binaries.## Code Generation Efficiency
- **No full rewrites:** When modifying code, output only the specific lines or functions that need changing. Do not rewrite the entire file.
- **Skip verbose explanations:** Provide the code fix first, followed by a maximum of 2 bullet points explaining the change.
- **Disable auto-linting loops:** Do not automatically run test suites or linters after every single change unless instructed.