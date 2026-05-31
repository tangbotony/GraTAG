import datetime
import json
import unittest
from app import app
from werkzeug.datastructures import FileStorage


with open("test_config.json", "r") as json_file:
    test_config = json.load(json_file)

test_login_credentials = test_config["test_login_credentials"]
admin_credentials = test_config["admin_credentials"]
AI_base = test_config["AI_base"]


class Test_app(unittest.TestCase):
    # Set up tset app
    def setUp(self):
        self.app = app
        self.appctx = self.app.app_context()
        self.appctx.push()
        self.client = self.app.test_client()

    # Stop runnning test app
    def tearDown(self):
        headers = self.auth()
        response = self.client.delete("/api/trash/all", headers=headers)
        self.appctx.pop()
        self.app = None
        self.appctx = None

    # auth func for normal user
    def auth(self):
        response = self.client.post(
            "/api/login",
            data=json.dumps(test_login_credentials),
            content_type="application/json",
        )
        response_data = json.loads(response.data)
        access_token = response_data.get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        return headers

    # auth func for admin
    def admin_auth(self):
        response = self.client.post(
            "/api/login",
            data=json.dumps(admin_credentials),
            content_type="application/json",
        )
        response_data = json.loads(response.data)
        access_token = response_data.get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        return headers

    # Test login with correct info
    def test_login_with_valid_credentials(self):
        response = self.client.post(
            "/api/login",
            data=json.dumps(test_login_credentials),
            content_type="application/json",
        )
        self.assertIn(b"access_token", response.data)
        self.assertIn(b"refresh_token", response.data)
        self.assertEqual(response.status_code, 200)

    # Test login with incorrect info
    def test_login_with_invalid_credentials(self):
        credentials = {"name": "llm1@qq.com", "passwd": "321"}
        response = self.client.post(
            "/api/login", data=json.dumps(credentials), content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    # Test Check user data
    def test_check_user_data_valid(self):
        response = self.client.get("/api/user", headers=self.auth())
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(
            response_data["userinfo"]["_id"], test_login_credentials["name"]
        )

    # Test Check for invalid data
    def test_check_user_data_invalid(self):
        headers = {
            "Authorization": "xxxxx"
        }
        response = self.client.get("/api/user", headers=headers)
        self.assertEqual(response.status_code, 401)

    # Test log out
    def test_log_out(self):
        response = self.client.post(
            "/api/login",
            data=json.dumps(test_login_credentials),
            content_type="application/json",
        )
        response_data = json.loads(response.data)
        access_token = response_data.get("access_token")
        refresh_token = response_data.get("refresh_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {"refresh": refresh_token}
        response = self.client.post("/api/logout", headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = self.client.get("/api/refresh", headers=headers)
        self.assertEqual(response.status_code, 401)

    # Test refresh
    def test_refresh_token(self):
        response = self.client.post(
            "/api/login",
            data=json.dumps(test_login_credentials),
            content_type="application/json",
        )
        response_data = json.loads(response.data)
        access_token = response_data.get("access_token")
        refresh_token = response_data.get("refresh_token")
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = self.client.get("/api/refresh", headers=headers)
        self.assertEqual(response.status_code, 200)

    # Test for valid folder creation
    def test_folder_creation_valid(self):
        headers = self.auth()
        # Create folder
        folder_name = "test_folder"
        folder_data = {"name": folder_name, "parent_id": "-1"}
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertIsNotNone(response_data["folder_id"])
        folder_id = response_data["folder_id"]

        # Check if created folder exists
        response = self.client.get("/api/folder/-1", headers=headers)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()["meta"]
        has_folder = False
        for element in response_data:
            if element["_id"] == folder_id:
                has_folder = True
                break
        self.assertTrue(has_folder)

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

    # Test for invalid creation
    def test_folder_creation_invalid(self):
        folder_data_invalid = {"name": "Test Folder", "parent_id": "0"}
        response = self.client.post(
            "/api/folder", json=folder_data_invalid, headers=self.auth()
        )
        self.assertEqual(response.status_code, 500)

    # Test for valid folder edit
    def test_folder_edit_valid(self):
        folder_name_1 = "test_folder"
        folder_name_2 = "test_folder_edit"
        headers = self.auth()
        # Create new folder for edit
        folder_data = {"name": folder_name_1, "parent_id": "-1"}
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        folder_id = json.loads(response.data)["folder_id"]

        # Edit folder
        response = self.client.put("/api/folder")
        data = {"id": folder_id, "name": folder_name_2, "parent_id": "-1"}
        response = self.client.put("/api/folder", headers=headers, json=data)
        self.assertEqual(response.status_code, 200)

        # Find edited folder
        response = self.client.get("/api/folder/-1", headers=headers)
        response_data = response.get_json()["meta"]
        for element in response_data:
            if element["_id"] == folder_id:
                self.assertNotEqual(element["name"], folder_name_1)
                self.assertEqual(element["name"], folder_name_2)
                break

        # Delte folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

    # Tests for invalid folder edit
    def test_folder_edit_invalid(self):
        folder_name_1 = "test_folder"
        folder_data = {"name": folder_name_1, "parent_id": "-1"}
        headers = self.auth()
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        folder_id = json.loads(response.data)["folder_id"]

        # Test for invalid parent id
        data = {
            "id": folder_id,
            "name": "test folder edit",
            "parent_id": "invalidParentID",
        }
        response = self.client.put("/api/folder", headers=headers, json=data)
        self.assertEqual(response.status_code, 400)

        # Test for invalid folder id
        data = {"id": "InvalidFOlderID", "name": "test folder edit", "parent_id": "-1"}
        response = self.client.put("/api/folder", headers=headers, json=data)
        self.assertEqual(response.status_code, 500)

        # Delte folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

    # Test for valid folder deletion
    def test_folder_delete_valid(self):
        # Create folder
        headers = self.auth()
        folder_name = "test_folder"
        folder_data = {"name": folder_name, "parent_id": "-1"}
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        folder_id = json.loads(response.data)["folder_id"]

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)
        self.assertEqual(response.status_code, 200)

        # Check folder is not in main dir
        response = self.client.get("/api/folder/-1", headers=headers)
        response_data = response.get_json()["meta"]
        has_folder = False
        for element in response_data:
            if element["_id"] == folder_id:
                has_folder = True
        self.assertFalse(has_folder)

        # Check folder is in trash
        response = self.client.get("/api/trash", headers=headers)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIsNotNone(response_data["trash_file"])
        has_folder = False
        for element in response_data["trash_file"]:
            if element["_id"] == folder_id:
                has_folder = True
        self.assertTrue(has_folder)

    # Test for invalid folder deletion
    def test_folder_delete_invalid(self):
        route_delete = f"api/folder/invalidID"
        response = self.client.delete(route_delete, headers=self.auth())
        self.assertEqual(response.status_code, 500)

    # Test for valid folder recovery
    def test_folder_recover(self):
        # Create folder
        headers = self.auth()
        folder_name = "test_folder"
        folder_data = {"name": folder_name, "parent_id": "-1"}
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        folder_id = json.loads(response.data)["folder_id"]

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

        # Test for recover deleted folder
        recover_route = f"/api/recover/folder/{folder_id}"
        data = {"id": folder_id}
        response = self.client.get(recover_route, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data["id"], folder_id)

        # Check if folder is recovered
        response = self.client.get("/api/folder/-1", headers=headers)
        response_data = response.get_json()["meta"]
        has_folder = False
        for element in response_data:
            if element["_id"] == folder_id:
                has_folder = True
                break
        self.assertTrue(has_folder)

        # Check folder does not exist in trash
        response = self.client.get("/api/trash", headers=headers)
        response_data = response.get_json()["trash_file"]
        has_folder = False
        if response_data:
            for element in response_data:
                if element["_id"] == folder_id:
                    has_folder = True
        self.assertFalse(has_folder)

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

    # Test for invalid folder recovery
    def test_folder_recover_invalid(self):
        recover_route = f"/api/recover/folder/invalidFolder"
        data = {"id": "invalidFolder"}
        response = self.client.get(recover_route, headers=self.auth(), data=data)
        self.assertEqual(response.status_code, 500)

    # Test for folder complete deletion
    def test_folder_complete_delete(self):
        # Create folder
        headers = self.auth()
        folder_name = "test_folder"
        folder_data = {"name": folder_name, "parent_id": "-1"}
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        folder_id = json.loads(response.data)["folder_id"]

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

        # Test for complete deletion
        data = {"id": folder_id}
        route_trash_delete = f"api/trash/folder/{folder_id}"
        response = self.client.delete(route_trash_delete, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data["id"], folder_id)

        # Check folder not in trash
        response = self.client.get("/api/trash", headers=headers)
        response_data = response.get_json()["trash_file"]
        has_folder = False
        if response_data:
            for element in response_data:
                if element["_id"] == folder_id:
                    has_folder = True
        self.assertFalse(has_folder)

    # Test for invalid complete folder deletion
    def test_folder_complete_delete_invalid(self):
        # Create folder
        headers = self.auth()
        folder_name = "test_folder"
        folder_data = {"name": folder_name, "parent_id": "-1"}
        response = self.client.post("/api/folder", json=folder_data, headers=headers)
        folder_id = json.loads(response.data)["folder_id"]

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

        # Delete folder from trash
        data = {"id": folder_id}
        route_trash_delete = f"api/trash/folder/{folder_id}"
        response = self.client.delete(route_trash_delete, headers=headers, data=data)

        # Check the folder cannot be deleted from trash
        response = self.client.delete(route_trash_delete, headers=headers, data=data)
        self.assertTrue(response.status_code, 500)

        # Delete folder
        route_delete = f"api/folder/{folder_id}"
        response = self.client.delete(route_delete, headers=headers)

    # Test for document creation
    def test_document_create(self):
        # Create test doc
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        doc_id = response_data["doc_id"]

        # Check document is created through doc search
        search_data = {"search_text": "test", "parent_id": "-1"}
        response = self.client.post(
            "/api/search/document", headers=headers, json=search_data
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()["meta"]
        has_doc = False
        for doc in response_data:
            if doc["_id"] == doc_id:
                has_doc = True
                # Delete doc
            temp = doc["_id"]
            doc_route = f"/api/document/{temp}"
            data = {"id": temp}
            response = self.client.delete(doc_route, headers=headers, data=data)
            # break
        self.assertTrue(has_doc)

        # Delete doc
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}
        response = self.client.delete(doc_route, headers=headers, data=data)

    # Test for invalid document creation
    def test_doc_create_invalid(self):
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {
            "name": test_doc_name,
            "text": test_doc_content,
            "parent_id": "invalidID",
        }
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    # Test for empty search
    def test_search_doc_empty(self):
        headers = self.auth()
        search_data = {"search_text": "这搜的什么玩意", "parent_id": "-1"}
        response = self.client.post(
            "/api/search/document", headers=headers, json=search_data
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data["meta"], [])

    # Test for valid document fetch
    def test_doc_fetch(self):
        # Create test doc
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        doc_id = response.get_json()["doc_id"]

        # Test for fetching created doc
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}
        response = self.client.get(doc_route, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()["doc"]
        self.assertEqual(response_data["_id"], doc_id)
        self.assertEqual(response_data["name"], test_doc_name)
        self.assertEqual(response_data["text"], test_doc_content)

        # Delete doc
        response = self.client.delete(doc_route, headers=headers, data=data)

    # Test for invalid document fetch
    def test_doc_fetch_invalid(self):
        doc_route = f"/api/document/invalidDOc"
        data = {"id": "invalidDOC"}
        response = self.client.get(doc_route, headers=self.auth(), data=data)
        self.assertEqual(response.status_code, 500)

    # Test for valid doc edit
    def test_doc_edit_valid(self):
        # Create test doc
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        doc_id = response.get_json()["doc_id"]
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}

        # Test for doc edit
        test_doc_name_edit = "test1"
        test_doc_content_edit = "This is the edited test doc"
        edit_data = {
            "id": doc_id,
            "name": test_doc_name_edit,
            "text": test_doc_content_edit,
        }
        response = self.client.put("/api/document", headers=headers, json=edit_data)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(doc_route, headers=headers, data=data)
        response_data = response.get_json()["doc"]
        self.assertEqual(response_data["name"], test_doc_name_edit)
        self.assertEqual(response_data["text"], test_doc_content_edit)

        # Delete doc
        response = self.client.delete(doc_route, headers=headers, data=data)

    # Test for invalid doc edit
    def test_doc_edit_invalid(self):
        test_doc_name_edit = "test1"
        test_doc_content_edit = "This is the edited test doc"
        headers = self.auth()
        edit_data = {
            "id": "invalidID",
            "name": test_doc_name_edit,
            "text": test_doc_content_edit,
        }
        response = self.client.put("/api/document", headers=headers, json=edit_data)
        self.assertEqual(response.status_code, 400)

    # Test for doc deletion
    def test_doc_delete(self):
        # Create test doc
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        doc_id = response.get_json()["doc_id"]
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}

        # delete doc
        response = self.client.delete(doc_route, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)

        # Check through doc fetch
        response = self.client.get(doc_route, headers=self.auth(), data=data)
        self.assertEqual(response.status_code, 500)

        # Check through garbage search
        response = self.client.get("/api/trash", headers=headers)
        response_data = response.get_json()
        has_doc = False
        for element in response_data["trash_file"]:
            if element["_id"] == doc_id:
                has_doc = True
        self.assertTrue(has_doc)

    # Test for invalid doc deletion
    def test_doc_delete_invalid(self):
        doc_id = "INvaLid1D"
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}
        response = self.client.delete(doc_route, headers=self.auth(), data=data)
        self.assertEqual(response.status_code, 500)

    # Test for document recovery
    def test_doc_recover(self):
        # Create test doc
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        doc_id = response.get_json()["doc_id"]
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}

        # delete doc
        response = self.client.delete(doc_route, headers=headers, data=data)

        # Test for doc recovery
        recover_route = f"/api/recover/document/{doc_id}"
        response = self.client.get(recover_route, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data["status"], 1)
        response = self.client.get(doc_route, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()["doc"]
        self.assertEqual(response_data["_id"], doc_id)
        self.assertEqual(response_data["name"], test_doc_name)
        self.assertEqual(response_data["text"], test_doc_content)

        # Delete doc
        response = self.client.delete(doc_route, headers=headers, data=data)

    # Test for invalid document recovery
    def test_doc_recover_invalid(self):
        doc_id = "INvaLid1D"
        data = {"id": doc_id}
        recover_route = f"/api/recover/document/{doc_id}"
        response = self.client.get(recover_route, headers=self.auth(), data=data)
        self.assertEqual(response.status_code, 500)

    # Test for complete document deletion
    def test_doc_delete_complete(self):
        # Create test doc
        test_doc_name = "test"
        test_doc_content = "This is a test doc."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        doc_id = response.get_json()["doc_id"]
        doc_route = f"/api/document/{doc_id}"
        data = {"id": doc_id}

        # delete doc
        response = self.client.delete(doc_route, headers=headers, data=data)

        # Test for complete doc deletion
        doc_delete_route = f"/api/trash/document/{doc_id}"
        response = self.client.delete(doc_delete_route, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/trash", headers=headers)
        response_data = response.get_json()["trash_file"]
        has_doc = False
        if response_data:
            for element in response_data:
                if element["_id"] == doc_id:
                    has_doc = True
        self.assertFalse(has_doc)

    # Test for invalid complete doc deletion
    def test_doc_delete_complete_invalid(self):
        doc_id = "INvaLid1D"
        data = {"id": doc_id}
        doc_delete_route = f"/api/trash/document/{doc_id}"
        response = self.client.delete(doc_delete_route, headers=self.auth(), data=data)
        self.assertTrue(response.status_code, 500)

    # # Test for delete all trash
    def trash_clear_all(self):
        # Create test doc
        test_doc_name = "test_del"
        test_doc_content = "This is a test doc for deletion."
        headers = self.auth()
        doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
        response = self.client.post("/api/document", json=doc_data, headers=headers)
        response_data = response.get_json()
        doc_id = response_data["doc_id"]
        data = {"id": doc_id}
        doc_route = f"/api/document/{doc_id}"

        # Delete test doc
        response = self.client.delete(doc_route, headers=headers, data=data)

        # Delete all trash
        response = self.client.delete("/api/trash/all", headers=headers)
        self.assertEqual(response.status_code, 200)

        # Check Trash is empty
        response = self.client.get("/api/trash", headers=headers)
        response_data = response.get_json()
        self.assertIsNone(response_data["trash_file"])

    # Test for clear all trash invalid
    def test_empty_trash_clear_all(self):
        headers = self.auth()
        response = self.client.get("/api/trash", headers=headers)
        response_data = response.get_json()
        if response_data["trash_file"]:
            response = self.client.delete("/api/trash/all", headers=headers)

        # Test for invalid clear_all
        response = self.client.delete("/api/trash/all", headers=headers)
        self.assertEqual(response.status_code, 500)

    # Test for feedback
    def test_feedback(self):
        headers = self.auth()
        feedback = {
            "brief": "自动测试",
            "contact": "test",
            "description": "自动测试" + str(datetime.datetime.now()),
        }
        response = self.client.post("/api/feedback", json=feedback, headers=headers)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()["feedback"]
        self.assertIsNotNone(response_data)
        self.assertEqual(response_data["brief"], feedback["brief"])
        self.assertEqual(response_data["contact"], feedback["contact"])
        self.assertEqual(response_data["description"], feedback["description"])

    # Test for invalid feedback
    def test_feedback_invalid(self):
        headers = self.auth()
        feedback = {"brief": "", "contact": "test", "description": ""}
        response = self.client.post("/api/feedback", json=feedback, headers=headers)
        self.assertEqual(response.status_code, 400)

    # Test for admin shared doc
    # def test_admin_share_and_delete_doc(self):
    #     headers = self.admin_auth()

    #     # Create test doc
    #     test_doc_name = "test admin" + str(datetime.datetime.now())
    #     test_doc_content = "This is a test doc."
    #     doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
    #     response = self.client.post("/api/document", json=doc_data, headers=headers)
    #     doc_id = response.get_json()["doc_id"]
    #     doc_route = f"/api/document/{doc_id}"
    #     data = {"doc_id": doc_id}

    #     # Share doc
    #     response = self.client.post("/share/document", headers=headers, json=data)
    #     self.assertEqual(response.status_code, 200)

    #     # Check doc exists in other users' dir
    #     search_data = {"search_text": test_doc_name, "parent_id": "-1"}
    #     response = self.client.post(
    #         "/api/search/document", headers=self.auth(), json=search_data
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     response_data = response.get_json()["meta"]
    #     self.assertIsNotNone(response_data)

    #     # delete shared doc
    #     response = self.client.post("/delete/document", headers=headers, json=data)
    #     self.assertEqual(response.status_code, 200)
    #     response = self.client.delete(doc_route, headers=headers, data=data)

    # # Test for non-admin user to share doc
    # def test_admin_share_doc_unauthorized(self):
    #     headers = self.auth()

    #     # Create test doc
    #     test_doc_name = "test admin"
    #     test_doc_content = "This is a test doc."
    #     doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
    #     response = self.client.post("/api/document", json=doc_data, headers=headers)
    #     doc_id = response.get_json()["doc_id"]
    #     data = {"doc_id": doc_id}

    #     response = self.client.post("/share/document", headers=headers, json=data)
    #     self.assertEqual(response.status_code, 400)

    # # Test for sharing invalid doc
    # def test_admin_share_doc_invalid(self):
    #     data = {"doc_id": "invalidID"}
    #     response = self.client.post(
    #         "/share/document", headers=self.admin_auth(), json=data
    #     )
    #     self.assertEqual(response.status_code, 500)

    # # Test for unauthorized delete doc
    # def test_admin_delete_shared_doc_unauthorized(self):
    #     headers = self.auth()

    #     # Create test doc
    #     test_doc_name = "test admin"
    #     test_doc_content = "This is a test doc."
    #     doc_data = {"name": test_doc_name, "text": test_doc_content, "parent_id": "-1"}
    #     response = self.client.post("/api/document", json=doc_data, headers=headers)
    #     doc_id = response.get_json()["doc_id"]
    #     data = {"doc_id": doc_id}

    #     response = self.client.post("/delete/document", headers=headers, json=data)
    #     self.assertEqual(response.status_code, 400)

    # # Test for deleting invalid doc
    # def test_admin_delete_shared_doc_invalid(self):
    #     data = {"doc_id": "invalidID"}
    #     response = self.client.post(
    #         "/delete/document", headers=self.admin_auth(), json=data
    #     )
    #     self.assertEqual(response.status_code, 500)

    # Test for basic continue write
    # def test_basic_continue_write(self):
    #     response = self.client.post(
    #         "/api/ai/basic_continue_write", headers=self.auth(), json=AI_base
    #     )
    #     self.assertEqual(response.status_code, 200)

    # # Test for basic expand write
    # def test_basic_expand_write(self):
    #     response = self.client.post(
    #         "/api/ai/basic_expand_write", headers=self.auth(), json=AI_base
    #     )
    #     self.assertEqual(response.status_code, 200)

    # # Test for basic polish write
    # def test_basic_polish_write(self):
    #     response = self.client.post(
    #         "/api/ai/basic_polish_write", headers=self.auth(), json=AI_base
    #     )
    #     self.assertEqual(response.status_code, 200)

    # # Test for pro continue write
    # def test_pro_continue_write(self):
    #     response = self.client.post(
    #         "/api/ai/pro_continue_write", headers=self.auth(), json=AI_base
    #     )
    #     self.assertEqual(response.status_code, 200)

    # # Test for basic continue write with reference
    # def test_basic_continue_write_ref(self):
    #     response = self.client.post(
    #         "/api/ai/basic_continue_write_reference", headers=self.auth(), json=AI_base
    #     )
    #     self.assertEqual(response.status_code, 200)

    # # Test for pro continue write with reference
    # def test_pro_continue_write_ref(self):
    #     response = self.client.post(
    #         "/api/ai/pro_continue_write_reference", headers=self.auth(), json=AI_base
    #     )
    #     self.assertEqual(response.status_code, 200)

    # Test for uploading files
    # def test_upload(self):
    #     access_token, refresh_token = self.login()
    #     headers = {"Authorization": f"Bearer {access_token}"}

    #     with open('test_files/test.pdf', 'rb') as file:
    #         uploaded_file = FileStorage(file, content_type='application/pdf', filename='test.pdf')
    #         response = self.client.post('/api/upload',data={'file': (uploaded_file, 'test.pdf')},headers=headers)
    #         self.assertEqual(response.status_code, 200)
    #         response_data = response.get_json()
    #         self.assertTrue('doc_id' in response_data)
    #         self.assertNotEqual(response_data['doc_id'], '')

    #     with open('test_files/test.docx', 'rb') as file:
    #         uploaded_file = FileStorage(file, content_type='application/docx', filename='test.docx')
    #         response = self.client.post('/api/upload',data={'file': (uploaded_file, 'test.docx')},headers=headers)
    #         self.assertEqual(response.status_code, 200)
    #         response_data = response.get_json()
    #         self.assertTrue('doc_id' in response_data)
    #         self.assertNotEqual(response_data['doc_id'], '')

    # Test for uploading image
    # def test_upload_image(self):
    #     access_token, refresh_token = self.login()
    #     headers = {"Authorization": f"Bearer {access_token}"}

