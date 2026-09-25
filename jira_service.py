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

            description_document = {

                "type": "doc",

                "version": 1,

                "content": [

                    {
                        "type": "paragraph",

                        "content": [

                            {
                                "type": "text",

                                "text":
                                    str(description)
                            }

                        ]
                    }

                ]
            }


            # =================================================
            # PAYLOAD
            # =================================================

            payload = {

                "fields": {

                    "project": {
                        "key":
                            self.project_key
                    },

                    "summary":
                        str(summary),

                    "description":
                        description_document,

                    "issuetype": {
                        "name":
                            "Task"
                    }

                }
            }


            headers = {

                "Accept":
                    "application/json",

                "Content-Type":
                    "application/json"
            }


            print(
                "Creating Jira ticket..."
            )

            print(
                "Jira endpoint:",
                endpoint
            )

            print(
                "Project:",
                self.project_key
            )


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

                issue_key = data.get(
                    "key"
                )


                issue_url = (
                    f"{self.url}"
                    f"/browse/{issue_key}"
                )


                print(
                    "JIRA TICKET CREATED:",
                    issue_key
                )


                return {

                    "success":
                        True,

                    "ticket_id":
                        issue_key,

                    "issue_key":
                        issue_key,

                    "issue_url":
                        issue_url,

                    "message":
                        (
                            "Jira ticket created "
                            f"successfully: {issue_key}"
                        )
                }


            # =================================================
            # JIRA ERROR
            # =================================================

            print(
                "JIRA RESPONSE:",
                response.text
            )


            return {

                "success":
                    False,

                "status_code":
                    response.status_code,

                "message":
                    (
                        "Jira API error "
                        f"({response.status_code}): "
                        f"{response.text}"
                    )
            }


        except requests.exceptions.Timeout:

            print(
                "JIRA ERROR: Request timed out."
            )

            return {

                "success":
                    False,

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

                "message":
                    str(error)
            }