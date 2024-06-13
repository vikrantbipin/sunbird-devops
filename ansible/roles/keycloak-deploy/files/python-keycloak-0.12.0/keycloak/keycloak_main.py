import json
import urllib.request
import argparse

from keycloak import KeycloakOpenID
from keycloak import KeycloakAdmin

# Import realm
def keycloak_import_realm(keycloak_realm_file):
    data = json.load(open(keycloak_realm_file))
    realm_import = keycloak_admin.import_realm(data)

# Add user and set password
def keycloak_create_user(email, username, firstName, lastName, password):
    new_user = keycloak_admin.create_user({"email": email,
                    "username": username,
                    "emailVerified": True,
                    "enabled": True,
                    "firstName": firstName,
                    "lastName": lastName,
                    "credentials": [{"value": password, "type": "password"}],
                    "realmRoles": ["user_default"]})

# Create the user and assign the role to access the user management API
def update_user_roles(config):
    realm_json = json.load(open(config['keycloak_realm_json_file_path']))

    # Get the id of realm-management
    client_id = None
    for client in realm_json['clients']:
        if config['clientId'] == client['clientId']:
            client_id = client["id"]
            break

    if client_id is None:
        raise ValueError("Client ID not found in realm JSON")

    user = keycloak_admin.get_users({"username": config['keycloak_api_management_username']})
    user_id = user[0]['id']

    # Read the role from file
    with open(config['keycloak_user_manager_roles_json_file_path'], 'r') as data_file:
        json_data = data_file.read()

    roles = json.loads(json_data)

    # Get only client roles
    client_roles = roles[config['clientId']]

    keycloak_admin.assign_client_role(user_id, client_id, client_roles)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Configure keycloak user APIs')
    parser.add_argument('keycloak_bootstrap_config', help='Configuration JSON file needed for keycloak bootstrap')
    args = parser.parse_args()

    with open(args.keycloak_bootstrap_config) as keycloak_bootstrap_config:
        config = json.load(keycloak_bootstrap_config)

    try:
        # Get access token
        keycloak_admin = KeycloakAdmin(server_url=config['keycloak_auth_server_url'],
                                       username=config['keycloak_management_user'],
                                       password=config['keycloak_management_password'],
                                       realm_name="master",
                                       client_id='admin-cli',
                                       verify=False)
        # Import realm
        keycloak_import_realm(config['keycloak_realm_json_file_path'])

        # Set realm name to sunbird
        keycloak_admin.realm_name = config['keycloak_realm']

        # Add user for user API
        keycloak_create_user(email=config['keycloak_api_management_user_email'],
                             username=config['keycloak_api_management_username'],
                             firstName=config['keycloak_api_management_user_first_name'],
                             lastName=config['keycloak_api_management_user_last_name'],
                             password=config['keycloak_api_management_user_password'])

        # Update user roles for access user management APIs
        config['clientId'] = "realm-management"
        update_user_roles(config)

        # Update user roles for SSO
        config['clientId'] = "admin-cli"
        update_user_roles(config)
    # If Keycloak is returning the error realm does exist
    except Exception as e:
        if "409" in str(e):
            print("Skipping error: " + str(e))
        else:
            raise