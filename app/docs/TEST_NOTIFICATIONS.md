# Testing Guide for Notification System CSRF Fix

## Overview
This guide will help you test that the CSRF token fix is working correctly for the notification system.

## Prerequisites
- Flask application is running (`python app.py`)
- You are logged into the application
- Browser developer tools are open (F12)

## Test Steps

### 1. Verify CSRF Token Meta Tag
1. Open your browser and navigate to any page in DEFITECH
2. Right-click → "View Page Source" or press `Ctrl+U`
3. Search for `csrf-token` in the source
4. You should see: `<meta name="csrf-token" content="[LONG TOKEN STRING]" />`

✅ **Expected Result:** Meta tag exists with a non-empty token value

### 2. Test Mark as Read (Single Notification)
1. Open browser Developer Tools (F12)
2. Go to the **Network** tab
3. Click on any unread notification in the notification dropdown
4. In Network tab, find the request: `POST /api/notifications/[ID]/mark-read`
5. Click on the request → **Headers** tab
6. Look for `X-CSRFToken` in the Request Headers section

✅ **Expected Result:**
- Status Code: `200 OK` (not 400)
- Request Headers contain: `X-CSRFToken: [TOKEN VALUE]`
- Notification is marked as read (blue indicator disappears)

### 3. Test Mark All as Read
1. Make sure you have some unread notifications
2. Open the notification dropdown
3. Click "Marquer tout comme lu" button
4. Check Network tab for: `POST /api/notifications/mark-all-read`

✅ **Expected Result:**
- Status Code: `200 OK`
- All notifications are marked as read
- Badge count becomes 0
- Success toast appears: "Toutes les notifications ont été marquées comme lues"

### 4. Test Delete Single Notification
1. Open notification dropdown
2. Hover over a notification
3. Click the trash icon (🗑️) on the right
4. Check Network tab for: `DELETE /api/notifications/[ID]`

✅ **Expected Result:**
- Status Code: `200 OK`
- Notification disappears from the list
- Badge count updates accordingly

### 5. Test Clear All Notifications
1. Open notification dropdown
2. Click "Tout effacer" button
3. Confirm the dialog
4. Check Network tab for: `DELETE /api/notifications/clear-all`

✅ **Expected Result:**
- Status Code: `200 OK`
- All notifications are removed
- Badge shows 0
- Success toast appears: "Toutes les notifications ont été supprimées"

## Debugging Failed Tests

### If you see 400 BAD REQUEST errors:

#### Step 1: Verify CSRF Token is Being Sent
1. Open Network tab
2. Click on the failed request
3. Go to **Headers** → **Request Headers**
4. Check if `X-CSRFToken` header exists

**If NO X-CSRFToken header:**
- Clear browser cache (Ctrl+Shift+Delete)
- Hard refresh the page (Ctrl+F5)
- Check browser console for JavaScript errors

**If X-CSRFToken header EXISTS but still getting 400:**
- Check Flask logs for detailed error message
- Verify `WTF_CSRF_ENABLED=True` in your `.env` file
- Make sure you're logged in (session exists)

#### Step 2: Check JavaScript Console
1. Open Developer Tools → **Console** tab
2. Look for any errors related to:
   - "Cannot read property 'getAttribute' of null"
   - "getCSRFToken is not defined"
   - Any other JavaScript errors

**If errors exist:**
- Make sure `notifications.js` was updated correctly
- Clear browser cache and reload
- Check that the file is being served correctly (Network tab)

#### Step 3: Verify Flask Configuration
Open `app.py` and verify:
```python
app.config["WTF_CSRF_ENABLED"] = True
app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]
```

#### Step 4: Check Flask Logs
Look at the terminal where Flask is running. You should see:
```
127.0.0.1 - - [28/Oct/2025 11:XX:XX] "POST /api/notifications/24/mark-read HTTP/1.1" 200 -
```

**If you see 400 instead of 200:**
- Check for additional error messages in Flask logs
- Look for CSRF-related warnings

### If JavaScript doesn't execute:

1. **Check if notifications.js is loaded:**
   - Network tab → Filter by "JS"
   - Look for `notifications.js` with status 200

2. **Check for syntax errors:**
   - Console tab should show any JavaScript syntax errors
   - Fix any reported errors in the file

3. **Clear cache and hard reload:**
   - Chrome/Edge: Ctrl+Shift+Delete, then Ctrl+F5
   - Firefox: Ctrl+Shift+Delete, then Ctrl+Shift+R

## Manual Testing Checklist

- [ ] CSRF token meta tag exists in HTML
- [ ] Mark single notification as read (200 OK)
- [ ] Mark all notifications as read (200 OK)
- [ ] Delete single notification (200 OK)
- [ ] Clear all notifications (200 OK)
- [ ] X-CSRFToken header present in all requests
- [ ] No 400 errors in Network tab
- [ ] No JavaScript errors in Console
- [ ] Badge count updates correctly
- [ ] Toast notifications appear

## Advanced: Network Tab Analysis

### Example of a SUCCESSFUL request:

**Request:**
```
POST /api/notifications/24/mark-read HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
X-CSRFToken: ImY3ZjE2YzQzMjk5N2ExNGQ4MzIyZjk3ZTNhM2IxZTM2Y2NmOWY5NjUi.Z6....
Cookie: session=eyJ...
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "message": "Notification marked as read"
}
```

### Example of a FAILED request (before fix):

**Request:**
```
POST /api/notifications/24/mark-read HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
Cookie: session=eyJ...
```
*(Notice: No X-CSRFToken header)*

**Response:**
```
HTTP/1.1 400 BAD REQUEST
Content-Type: text/html

<title>400 Bad Request</title>
The CSRF token is missing.
```

## Performance Testing

1. **Load Test:** Open notification dropdown multiple times rapidly
   - Should not cause errors
   - Badge should update correctly each time

2. **Concurrent Actions:** Try marking as read while deleting another
   - Both actions should succeed
   - No race conditions

3. **Offline/Online:** Disable network, try action, re-enable network
   - Should show error message
   - Should retry successfully when online

## Success Criteria

✅ All API calls return **200 OK** instead of **400 BAD REQUEST**
✅ X-CSRFToken header is present in all POST/DELETE requests
✅ Notifications work correctly (mark as read, delete, etc.)
✅ No JavaScript errors in console
✅ Badge count updates in real-time
✅ Toast notifications appear on success/error

## Rollback Instructions

If the fix causes issues, revert the following files:

1. **templates/base.html** - Remove the CSRF meta tag line
2. **static/js/notifications.js** - Revert to previous version
3. **app.py** - Remove `WTF_CSRF_HEADERS` configuration

Or use git:
```bash
git checkout HEAD~1 templates/base.html
git checkout HEAD~1 static/js/notifications.js
git checkout HEAD~1 app.py
```

## Additional Resources

- Flask-WTF Documentation: https://flask-wtf.readthedocs.io/
- Chrome DevTools Network Tab: https://developer.chrome.com/docs/devtools/network/
- CSRF Explained: https://owasp.org/www-community/attacks/csrf

---

**Last Updated:** October 28, 2025
**Status:** Ready for Testing
  **Priority:** High
