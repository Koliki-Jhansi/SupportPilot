import os
import requests

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# JIRA SERVICE
# ============================================================

class JiraService:

    def __init__(self):

        self.url = os.getenv(
            "JIRA_URL",
            ""
        ).strip().rstrip("/")

        self.email = os.getenv(
            "JIRA_EMAIL",
            ""
        ).strip()

        self.api_token = os.getenv(
            "JIRA_API_TOKEN",
            ""
        ).strip()

        self.project_key = os.getenv(
            "JIRA_PROJECT_KEY",
            ""
        ).strip()


        # Safe debugging
        # Token itself is NEVER printed.

        print("=" * 60)
        print("JIRA CONFIGURATION")
        print("=" * 60)

        print(
            "JIRA URL:",
            repr(self.url)
        )

        print(
            "JIRA EMAIL:",
            repr(self.email)
        )

        print(
            "JIRA TOKEN LOADED:",
            bool(self.api_token)
        )

        print(
            "JIRA PROJECT:",
            repr(self.project_key)
        )

        print("=" * 60)


    # ========================================================
    # CHECK CONFIGURATION
    # ========================================================

    def is_configured(self):

        return bool(
            self.url
            and
            self.email
            and
            self.api_token
            and
            self.project_key
        )


    # ========================================================
    # CREATE JIRA TICKET
    # ========================================================

    def create_ticket(
        self,
        summary,
        description,
        priority="High"
    ):

        if isinstance(summary, dict):
            ticket_data = summary
            ticket_id = ticket_data.get("id", "")
            title = ticket_data.get("title", "Support Ticket")
            desc = ticket_data.get("description", "")
            priority = ticket_data.get("priority", priority or "High")

            summary = f"[SupportPilot #{ticket_id}] {title}"

            if isinstance(description, dict):
                diag = description.get("diagnosis", {})
                res = description.get("resolution", {})
                diag_text = diag.get("diagnosis", "") if isinstance(diag, dict) else str(diag)
                res_text = res.get("response", "") if isinstance(res, dict) else str(res)
                description = f"User Description:\n{desc}\n\nDiagnosis:\n{diag_text}\n\nResolution:\n{res_text}"
            elif not description:
                description = f"User Description:\n{desc}"

        if not self.is_configured():

            missing = []

            if not self.url:
                missing.append(
                    "JIRA_URL"
                )

            if not self.email:
                missing.append(
                    "JIRA_EMAIL"
                )

            if not self.api_token:
                missing.append(
                    "JIRA_API_TOKEN"
                )

            if not self.project_key:
                missing.append(
                    "JIRA_PROJECT_KEY"
                )


            message = (
                "Jira integration is not configured. "
                "Missing: "
                + ", ".join(missing)
            )

            print(
                "JIRA CONFIG ERROR:",
                message
            )

            return {
                "success": False,
                "message": message
            }


        try:

            # =================================================
            # JIRA CLOUD REST API
            # =================================================

            endpoint = (
                f"{self.url}"
                "/rest/api/3/issue"
            )


            # =================================================
            # ATLASSIAN DOCUMENT FORMAT
            # =================================================

            paragraphs = []
            for line in str(description).splitlines():
                if line.strip():
                    paragraphs.append({
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": line
                            }
                        ]
                    })

            if not paragraphs:
                paragraphs = [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "SupportPilot Escalated Ticket"
                            }
                        ]
                    }
                ]

            description_document = {
                "type": "doc",
                "version": 1,
                "content": paragraphs
            }

            # =================================================
            # PAYLOAD
            # =================================================

            payload = {
                "fields": {
                    "project": {
                        "key": self.project_key
                    },
                    "summary": str(summary),
                    "description": description_document,
                    "issuetype": {
                        "name": "Task"
                    }
                }
            }

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            print("Creating Jira ticket...")
            print("Jira endpoint:", endpoint)
            print("Project:", self.project_key)

            # =================================================
            # SEND REQUEST
            # =================================================

            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                auth=HTTPBasicAuth(
                    self.email,
                    self.api_token
                ),
                timeout=30
            )

            print(
                "JIRA HTTP STATUS:",
                response.status_code
            )

            # =================================================
            # SUCCESS
            # =================================================

            if response.status_code in (
                200,
                201
            ):
                data = response.json()
                issue_key = data.get("key")

                issue_url = (
                    f"{self.url}/browse/{issue_key}"
                )

                print(
                    "JIRA TICKET CREATED:",
                    issue_key
                )

                return {
                    "success": True,
                    "jira_status": "Created",
                    "ticket_id": issue_key,
                    "issue_key": issue_key,
                    "jira_key": issue_key,
                    "issue_url": issue_url,
                    "jira_url": issue_url,
                    "message": (
                        "Jira ticket created successfully: "
                        f"{issue_key}"
                    )
                }

            # =================================================
            # JIRA ERROR
            # =================================================

            error_details = ""
            try:
                err_json = response.json()
                error_messages = err_json.get("errorMessages", [])
                field_errors = err_json.get("errors", {})
                all_msgs = list(error_messages) + [f"{k}: {v}" for k, v in field_errors.items()]
                if all_msgs:
                    error_details = " – " + "; ".join(all_msgs)
            except Exception:
                error_details = f" – {response.text[:200]}"

            clean_error = f"Jira API error ({response.status_code}){error_details}"

            print(
                "JIRA RESPONSE:",
                clean_error
            )

            return {
                "success": False,
                "jira_status": "Failed",
                "status_code": response.status_code,
                "message": clean_error,
                "error": clean_error
            }


        except requests.exceptions.Timeout:

            print(
                "JIRA ERROR: Request timed out."
            )

            return {

                "success":
                    False,

                "jira_status": "Failed",

                "message":
                    "Jira request timed out."
            }


        except requests.exceptions.ConnectionError as error:

            print(
                "JIRA CONNECTION ERROR:",
                repr(error)
            )

            return {

                "success":
                    False,

                "jira_status": "Failed",

                "message":
                    (
                        "Could not connect to Jira: "
                        f"{error}"
                    )
            }


        except requests.RequestException as error:

            print(
                "JIRA REQUEST ERROR:",
                repr(error)
            )

            return {

                "success":
                    False,

                "jira_status": "Failed",

                "message":
                    (
                        "Jira request failed: "
                        f"{error}"
                    )
            }


        except Exception as error:

            print(
                "JIRA ERROR:",
                repr(error)
            )

            return {

                "success":
                    False,

                "jira_status": "Failed",

                "message":
                    str(error)
            }

    # ========================================================
    # SAFE DIAGNOSTIC CHECK
    # ========================================================

    def verify_jira_access(self):
        """
        Safely verifies Jira connectivity, authentication, and project access.
        Never logs or exposes tokens or secrets.
        """
        if not self.is_configured():
            return {
                "configured": False,
                "authenticated": False,
                "project_exists": False,
                "project_key": self.project_key,
                "url": self.url,
                "error": "Jira configuration is incomplete in environment."
            }

        try:
            # 1. Verify Authentication & User
            user_resp = requests.get(
                f"{self.url}/rest/api/3/myself",
                auth=HTTPBasicAuth(self.email, self.api_token),
                timeout=15
            )

            if user_resp.status_code != 200:
                return {
                    "configured": True,
                    "authenticated": False,
                    "project_exists": False,
                    "project_key": self.project_key,
                    "url": self.url,
                    "status_code": user_resp.status_code,
                    "error": f"Authentication failed (HTTP {user_resp.status_code}). Check JIRA_EMAIL and JIRA_API_TOKEN."
                }

            user_data = user_resp.json()
            display_name = user_data.get("displayName", self.email)

            # 2. Check accessible projects
            projects_resp = requests.get(
                f"{self.url}/rest/api/3/project",
                auth=HTTPBasicAuth(self.email, self.api_token),
                timeout=15
            )

            accessible_projects = []
            if projects_resp.status_code == 200:
                projects_list = projects_resp.json()
                if isinstance(projects_list, list):
                    accessible_projects = [
                        p.get("key") for p in projects_list if isinstance(p, dict) and p.get("key")
                    ]

            # 3. Check specific configured project
            proj_resp = requests.get(
                f"{self.url}/rest/api/3/project/{self.project_key}",
                auth=HTTPBasicAuth(self.email, self.api_token),
                timeout=15
            )

            project_exists = proj_resp.status_code == 200
            issue_types = []
            if project_exists:
                proj_data = proj_resp.json()
                issue_types = [
                    it.get("name")
                    for it in proj_data.get("issueTypes", [])
                    if isinstance(it, dict) and it.get("name")
                ]

            return {
                "configured": True,
                "authenticated": True,
                "user": display_name,
                "url": self.url,
                "project_key": self.project_key,
                "project_exists": project_exists,
                "accessible_projects": accessible_projects,
                "issue_types": issue_types,
                "message": (
                    f"Project '{self.project_key}' is accessible."
                    if project_exists
                    else f"Project '{self.project_key}' does not exist on {self.url}. Accessible projects: {accessible_projects or 'None'}"
                )
            }

        except Exception as err:
            return {
                "configured": True,
                "authenticated": False,
                "project_exists": False,
                "project_key": self.project_key,
                "url": self.url,
                "error": f"Connection error: {err}"
            }