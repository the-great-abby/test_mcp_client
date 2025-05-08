# 📊 MCP Chat Client Onboarding Analytics Dashboard

This dashboard summarizes onboarding analytics collected via `ai_ide_analytics.sh`.

---

## How to Update
Run the following script to generate the latest stats:
```sh
bash onboarding_analytics_summary.sh
```

---

## Example Analytics Summary

```
===============================
 MCP Chat Client Onboarding Analytics Summary
===============================
Total events logged: 42

Event counts:
   20 onboarding_started
   10 onboarding_completed
    7 feedback_submitted
    5 ran_first_run

Events by user type:
   30 ai-ide
   12 human

First event: 2024-04-01 09:00:00
Last event:  2024-05-08 15:30:00
```

---

> Use this dashboard to track onboarding trends and improve the experience for future contributors and AI-IDEs. For more details, see the analytics log (`ai_ide_analytics.log`). 