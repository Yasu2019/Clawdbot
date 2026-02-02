# API Error 429 Diagnosis Report

**Date:** 2026-02-02
**Issue:** User reported Error Code 429 (Too Many Requests).

## 🔍 Investigation

### 1. Active Hourly Jobs

We found two jobs scheduled to run every hour (`0 * * * *`):

- **A. Hourly_Email_Task_Check (Newly Added)**
  - Action: Runs `gmail_to_calendar.js`.
  - API Usage: Checks Gmail, then uses Gemini 2.0 to parse *every unread email*.
  - **Risk:** High. If there are many unread emails, this triggers a burst of API calls.
  
- **B. Hourly_API_Usage_Report (Disabled now)**
  - Action: Asks the Agent to check API usage on Google Cloud Console.
  - API Usage: The Agent consumes tokens to "think" about this request.
  - **Status:** **DISABLED**. The Agent cannot access the Cloud Console URL (it requires login), so this was wasting tokens fruitlessly every hour.

### 2. Suspicious Process on Host

- **Process:** `curl "https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyBgsqb..."`
- **Duration:** Running for **28+ hours**.
- **Analysis:** This looks like a hanging process on your main terminal/console. If it is stuck in a retry loop, it could be hammering the API.
- **Recommendation:** Please close any open terminals or kill this `curl` process.

## 🛠 Actions Taken

1. **Disabled `Hourly_API_Usage_Report`**: This was generating unnecessary load and likely failing/retrying.
2. **Gmail Optimization Recommnedation**: currently `gmail_to_calendar.js` processes `newer_than:1h`. This is generally safe ($0.00 cost if no emails).

## 📉 Conclusion

The "Error 429" is likely a combination of:

1. The **Ghost Curl Process** (28h) eating connections/quota?
2. The **Agent waking up hourly** for the Usage Report (now disabled).

**Next Step:** Monitor if errors persist after disabling the Usage Report job.
