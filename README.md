# Work Hour Tracker
A basic server for tracking your work hours

## Setup
### Docker Compose
It is important to pass the local time and timezone through to the container. Otherwise calculations might be wrong
```yaml
services:
    time_tracker:
        container_name: time_tracker
        image: ghcr.io/tomw1605/time_tracker:master
        ports:
          - "5000:5000"
        environment:
          - PORT=5000
          - BASE_URL=/time_tracker
          - HOURS_PER_DAY=7.6
          - HOURS_PER_WEEK=38
          - TZ=Australia/Perth
        volumes:
          - ${PWD}/configs/time_tracker:/config
          - /etc/timezone:/etc/timezone:ro
          - /etc/localtime:/etc/localtime:ro
        restart: unless-stopped
```
## Usage
Once started, the server works as a single page application. The main page has expandable sections for manually logging hours, clocking in, clocking out and showing a summary (the summary is expanded by default).

The summary is grouped by weeks, with total hours calculated per week. The hours over/under for a week are also displayed. The target hours for days and weeks can be set through environment variables. 

### Editing
Shifts can also be edited and deleted. From the summary table the edit link will go to an edit page where details of the shift can be changed. The delete buttons will simply delete the shift completely. WARNING, this can not be undone. 

### iOS Shortcuts
One of the main goals for me with this program was to be able to clock in and out from an iOS shortcut on my phone.
This allowed me to also automatically set notifications for when to leave dynamically from hours worked.
Links to the shortcuts i use can be found below:
- [Clock In](https://www.icloud.com/shortcuts/203f1215cd7943a8a952424a603080ff) 
- [Clock Out](https://www.icloud.com/shortcuts/4670679046274c5a943a40e2aed86269)
- [Start Break](https://www.icloud.com/shortcuts/d9dbde2e6ae54ed9a651f3f932a245ee)
- [End Break](https://www.icloud.com/shortcuts/17868944280244a187640fc2ed26bc3d)

As the program doesn't actually support breaks (it is on the to do list), the break shortcuts are simply clocking out and back in.
With the End Break shortcut updating the leave work reminder to account for the added break time.

#### Scriptable
All of these shortcuts rely on a [Scriptable](https://scriptable.app/) scrip, [post to URL.js](post%20to%20URL.js).\
As such, you must install the Scriptable app and load this script into it before the shortcuts above will work.

## API
### 1. Log Worked Hours Manually
#### POST `/api/log_hours`
Logs work hours manually.
- Request Body:
  ```json
  {
    "date": "YYYY-MM-DD",
    "hours_worked": 5.5
  }
  ```
- Response:
  ```json
  {
    "message": "Work hours logged successfully."
  }
  ```
### 2. Clock In
#### POST `/api/clock_in`
Clocks in at the specified time.\
Also calculates and returns an estimated leave time, based on hours expected in a day, hours worked today already and, if today is a Friday, hours worked this week already.
- Request Body:
  ```json
  {
    "clock_in_time": "HH:MM:SS"
  }
  ```
- Response:
  ```json
  {
    "message": "Clocked in successfully.",
    "leave_time": "HH:MM:SS"
  }
  ```
### 3. Clock Out
#### POST `/api/clock_out`
Clocks out at the specified time.
- Request Body:
  ```json
  {
    "clock_out_time": "HH:MM:SS"
  }
  ```
- Response:
  ```json
  {
    "message": "Clocked out successfully."
  }
  ```
### 4. Get Sessions
GET `/api/get_sessions`
Retrieves a summary of all work sessions.
- Response:
  ```json
  [
    {
      "id": 1,
      "session_type": "manual",
      "date": "YYYY-MM-DD",
      "hours_worked": 5.5,
      "clock_in_time": null,
      "clock_out_time": null
    },
    {
      "id": 2,
      "session_type": "clocked",
      "date": "YYYY-MM-DD",
      "hours_worked": 8.0,
      "clock_in_time": "YYYY-MM-DD HH:MM:SS",
      "clock_out_time": "YYYY-MM-DD HH:MM:SS"
    }
  ]
  ```
### 5. Get Sessions Grouped by Week
GET `/api/get_sessions_grouped`
Retrieves work sessions grouped by week.
- Response:
  ```json
  {
    "YYYY-MM-DD": {
      "start_date": "python date object",
      "start": "DD-MM-YYYY",
      "end": "DD-MM-YYYY",
      "hours_short": 24.5,
      "hours_worked": 13.5,
      "sessions": [
        {
          "id": 1,
          "session_type": "manual",
          "date": "YYYY-MM-DD",
          "hours_worked": 5.5,
          "clock_in_time": null,
          "clock_out_time": null
        },
        {
          "id": 2,
          "session_type": "clocked",
          "date": "YYYY-MM-DD",
          "hours_worked": 8.0,
          "clock_in_time": "YYYY-MM-DD HH:MM:SS",
          "clock_out_time": "YYYY-MM-DD HH:MM:SS"
        }
      ]
    }
  }
  ```
### 6. Get Hours Summary
GET `/api/get_hours`
Retrieves the total hours worked today and this week, and hours deficit for today, this week and all time.
- Response:
  ```json
  {
    "hours_today": 5.5,
    "hours_this_week": 40.0,
    "today_deficit": 2.1,
    "week_deficit": -2.0,
    "all_time_deficit": -10.0
  }
  ```
### 7. Delete Session
DELETE `/api/delete_session/<int:id>`
Deletes a work session by its ID.
- Response:
  ```json
  {
    "message": "Session deleted successfully."
  }
  ```
### 8. Get Session
#### GET `/api/get_session/<int:id>`
Retrieves a specific work session by its ID.
- URL Parameters:
  - id (integer): The ID of the session to retrieve.
- Response:
    ```json
    {
      "id": 1,
      "session_type": "clocked",
      "date": "2024-05-28",
      "hours_worked": 8.0,
      "clock_in_time": "08:00:00",
      "clock_out_time": "16:00:00"
    }
    ```
### 9. Edit Session
#### POST `/api/edit_session/<int:id>`
Edits a specific work session by its ID.
- URL Parameters:
  - id (integer): The ID of the session to edit.
- Request Body:
    ```json
    {
      "date": "2024-05-28",
      "hours_worked": 8.0,  // Only for 'hours' session type
      "clock_in_time": "08:00:00",  // Only for 'clocked' session type
      "clock_out_time": "16:00:00"  // Only for 'clocked' session type
    }
    ```
- Response:
    ```json
    {
      "message": "Session updated successfully"
    }
    ```

### License
This project is licensed under the GNU-3.0 License. See the LICENSE file for more details.
