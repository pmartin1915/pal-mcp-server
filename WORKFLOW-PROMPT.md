# Multi-Model Workflow Prompt Template

> Copy and customize the prompt below for your project sessions.
> This workflow maximizes Claude Max productivity by using the right model for each task.

---

## Quick-Start Prompt (Copy This)

```
## Project Context
I am working on [PROJECT_NAME]. [Brief description of current focus/feature].

## Multi-Model Workflow
Use this model strategy for maximum efficiency:

### Model Roles
| Model | Use For | How to Call |
|-------|---------|-------------|
| **Opus** (you) | Planning, architecture, complex decisions, debugging | Direct conversation |
| **Sonnet** | Implementation, refactoring, routine coding | Switch model or delegate |
| **Gemini 3 Pro** | Code review, large file analysis, outside perspective | `mcp__pal__chat` with model="gemini-3-pro-preview" |
| **Gemini Flash** | Quick iterations, simple queries, fallback | `mcp__pal__chat` with model="gemini-2.5-flash" |

### When to Use Gemini via PAL MCP
- Code review for security/performance issues
- Second opinion on architecture decisions
- Processing large files (1M token context)
- Fresh perspective from a different AI
- Heavy coding tasks to preserve Opus context

### Gemini Call Examples
```
# For code review
Use PAL chat with Gemini 3 Pro to review [file] for [security/performance/patterns]

# For implementation help
Ask Gemini 3 Pro via PAL to implement [feature] following [pattern]

# For quick checks
Use Gemini Flash via PAL to [simple task]
```

### Fallback Rule
If Gemini 3 Pro returns an error (quota/overloaded), retry with Gemini Flash.

## Session Management
- Keep plans within **40-70% of context window** (~80-140k tokens)
- Break large features into focused sessions
- Summarize progress at session end for handoff
- Use TodoWrite to track multi-step tasks

## Workflow
1. **Opus** reviews requirements and creates implementation plan
2. **Opus/Sonnet** implements code
3. **Gemini 3 Pro** reviews for issues and alternative approaches
4. **Opus** handles complex debugging or architectural decisions
5. Commit when feature complete

## Current Session
[Describe what you want to accomplish this session]

Take your time. Ask questions and give suggestions as needed.
```

---

## Project-Specific Versions

### Healthcare Education Apps
```
## Project Context
I am working on my healthcare education applications. Current focus: [burn-wizard/clinical-toolkit/etc].

## Multi-Model Workflow
[Same as above]

## Healthcare App Specifics
- Clinical accuracy is critical - verify medical information
- HIPAA considerations for any user data
- Accessibility requirements for healthcare settings
- Mobile-responsive for clinical environments

## Current Session
[Your task here]
```

### Land Auction Application (Alabama Auction Watcher)
```
## Project Context
I am working on the Alabama land auction application. Current focus: [feature/component].

## Multi-Model Workflow
[Same as above]

## Land Auction Specifics
- Data scraping reliability and error handling
- Real-time notification accuracy
- User authentication and saved searches
- Map/GIS integration considerations

## Current Session
[Your task here]
```

---

## PAL MCP Quick Reference

### Available Gemini Models
| Model | Alias | Best For |
|-------|-------|----------|
| `gemini-3-pro-preview` | `pro` | Complex reasoning, code review |
| `gemini-2.5-flash` | `flash` | Fast iterations, simple tasks |
| `gemini-2.5-pro` | - | Deep analysis |

### PAL Tools for Gemini
```
mcp__pal__chat          - General conversation/coding
mcp__pal__codereview    - Structured code review
mcp__pal__thinkdeep     - Complex problem analysis
mcp__pal__debug         - Debugging assistance
mcp__pal__analyze       - Code analysis
```

### Example PAL Calls
```python
# Simple chat
mcp__pal__chat(
    prompt="Review this function for edge cases: [code]",
    model="gemini-3-pro-preview",
    working_directory_absolute_path="C:\\Users\\perry\\project"
)

# Code review
mcp__pal__codereview(
    step="Reviewing authentication module for security issues",
    model="gemini-3-pro-preview",
    relevant_files=["C:\\Users\\perry\\project\\src\\auth.py"],
    ...
)
```

---

## Session Boundaries

### Signs You're Approaching Context Limit
- Responses becoming slower
- Claude forgetting earlier context
- Repetitive explanations needed

### When to Start New Session
- Major feature complete
- Context feels heavy (>70% used)
- Switching to unrelated feature
- After ~2-3 hours of intensive work

### Handoff Template
```
## Session Summary
- Completed: [list]
- In Progress: [list]
- Blocked: [list]
- Next Steps: [list]

## Key Files Modified
- [file1]: [what changed]
- [file2]: [what changed]

## Notes for Next Session
[Important context to remember]
```

---

## Troubleshooting

### Gemini Not Working
See: `C:\Users\perry\pal-mcp-server\PAL-MCP-SETUP.md`

### Switch Gemini API Key
```powershell
cd C:\Users\perry\pal-mcp-server
.\Switch-GeminiKey.ps1 -ApiKey "AIzaNewKey" -ProjectNumber "123456"
# Then restart VSCode
```

### Check Available Models
Ask Claude to run `mcp__pal__listmodels`
