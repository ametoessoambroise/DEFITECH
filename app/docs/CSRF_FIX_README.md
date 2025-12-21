# CSRF Token Fix for Notification System

## Problem
The notification system was experiencing **400 BAD REQUEST** errors when trying to:
- Mark notifications as read (`POST /api/notifications/<id>/mark-read`)
- Delete notifications (`DELETE /api/notifications/<id>`)
- Mark all notifications as read (`POST /api/notifications/mark-all-read`)
- Clear all notifications (`DELETE /api/notifications/clear-all`)

### Root Cause
The Flask application has **CSRF (Cross-Site Request Forgery) protection** enabled via Flask-WTF, but the JavaScript fetch requests were not including the required CSRF token. This caused all POST, PUT, DELETE, and PATCH requests to be rejected with a 400 error.

## Solution Implemented

### 1. Added CSRF Token Meta Tag
**File:** `templates/base.html`

Added a meta tag in the `<head>` section to make the CSRF token available to JavaScript:

```html
<meta name="csrf-token" content="{{ csrf_token() }}" />
```

### 2. Updated JavaScript to Include CSRF Token
**File:** `static/js/notifications.js`

Added the following changes:

#### a. Added CSRF Token Retrieval Method
```javascript
getCSRFToken() {
    if (!this.csrfToken) {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        this.csrfToken = metaTag ? metaTag.getAttribute('content') : '';
    }
    return this.csrfToken;
}
```

#### b. Updated All Fetch Requests
Added `'X-CSRFToken': this.getCSRFToken()` header to all POST, DELETE requests:

- `markAsRead(id)` - Mark single notification as read
- `markAllAsRead()` - Mark all notifications as read
- `deleteNotification(id)` - Delete single notification
- `clearAll()` - Delete all notifications

Example:
```javascript
const response = await fetch(`/api/notifications/${id}/mark-read`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken()
    },
    credentials: 'same-origin'
});
```

### 3. Configured Flask to Accept CSRF Token from Header
**File:** `app.py`

Added configuration to accept CSRF tokens from custom headers:

```python
app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]
```

This tells Flask-WTF to look for the CSRF token in the `X-CSRFToken` or `X-CSRF-Token` HTTP headers, in addition to form fields.

## How It Works

1. **Server-side:** Flask generates a unique CSRF token for each session
2. **Template:** The token is embedded in a meta tag in the HTML `<head>`
3. **Client-side:** JavaScript reads the token from the meta tag
4. **Request:** The token is sent with every AJAX request in the `X-CSRFToken` header
5. **Validation:** Flask-WTF validates the token and allows/denies the request

## Testing

After implementing these changes:

1. Clear your browser cache
2. Reload the page
3. Try the following actions:
   - Click on a notification to mark it as read ✅
   - Click the "Mark all as read" button ✅
   - Delete a single notification ✅
   - Clear all notifications ✅

All actions should now work without 400 errors.

## Security Notes

- **CSRF tokens are unique per session** - They prevent attackers from making unauthorized requests on behalf of authenticated users
- **Tokens are automatically regenerated** when the session changes
- **Same-origin policy** is enforced via `credentials: 'same-origin'` in fetch requests
- **Never disable CSRF protection** in production environments

## Alternative Solution (Not Recommended)

If you want to exempt specific API routes from CSRF protection (NOT RECOMMENDED for security reasons):

```python
from flask_wtf.csrf import csrf

@app.route("/api/notifications/<int:notification_id>/mark-read", methods=["POST"])
@csrf.exempt  # This disables CSRF protection for this route
@login_required
def api_mark_notification_read(notification_id):
    # ... route code
```

⚠️ **Warning:** Only use `@csrf.exempt` for public APIs that use alternative authentication methods (API keys, JWT tokens, etc.). Never exempt routes that rely on session-based authentication.

## Files Modified

1. ✅ `templates/base.html` - Added CSRF token meta tag
2. ✅ `static/js/notifications.js` - Updated to send CSRF token with requests
3. ✅ `app.py` - Configured Flask to accept CSRF token from headers

## Troubleshooting

### Still getting 400 errors?

1. **Check browser console** for any JavaScript errors
2. **Verify meta tag exists** - View page source and look for `<meta name="csrf-token" content="...">`
3. **Check network tab** - Verify that the `X-CSRFToken` header is being sent with requests
4. **Clear browser cache** and reload
5. **Check Flask logs** for more detailed error messages

### CSRF token is empty/null?

- Make sure you're logged in (CSRF tokens require an active session)
- Check that `{{ csrf_token() }}` is available in your Jinja2 template context
- Verify that Flask-WTF is properly initialized

## Related Documentation

- [Flask-WTF CSRF Protection](https://flask-wtf.readthedocs.io/en/stable/csrf.html)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [MDN - Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)

---

**Status:** ✅ Fixed
**Date:** October 28, 2025
**Impact:** All notification API endpoints now work correctly