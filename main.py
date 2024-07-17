import base64
import json
import os
import re
import sys
import time

from dotenv import load_dotenv
import requests

from models import EmoteSet, User


ENDPOINT = "https://7tv.io/v3"


def emote_set_from_id(emote_set_id: str) -> EmoteSet | None:
    url = f"{ENDPOINT}/emote-sets/{emote_set_id}"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Something went wrong fetching an emote set: {e}")
        sys.exit(1)
    result = response.json()
    return EmoteSet(**result)


def user_from_id(seventv_user_id: str) -> User | None:
    url = f"{ENDPOINT}/users/{seventv_user_id}"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Something went wrong fetching an emote set: {e}")
        sys.exit(1)
    result = response.json()
    return User(**result)


def add_emote(token: str, emote_set_id: str, emote_id: str, name: str) -> None:
    query = """
        mutation ChangeEmoteInSet($id: ObjectID! $action: ListItemAction! $emote_id: ObjectID!, $name: String) {
            emoteSet(id: $id) {
                emotes(id: $emote_id action: $action, name: $name) {
                    id
                    name
                }
            }
        }
    """
    variables = {
        "id": emote_set_id,
        "action": "ADD",
        "emote_id": emote_id,
        "name": name,
    }
    payload = {"query": query, "variables": variables}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{ENDPOINT}/gql"
    try:
        response = requests.post(url=url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Something went wrong adding an emote: {e}")
        sys.exit(1)
    data = response.json()
    if "errors" in data:
        print(f"An error occured while adding an emote: {data['errors'][0]['message']}")
        sys.exit(1)


def create_emote_set(token: str, name: str, user_id: str) -> str:
    query = """
        mutation CreateEmoteSet($user_id: ObjectID!, $data: CreateEmoteSetInput!) {
            createEmoteSet(user_id: $user_id, data: $data) {
                id
                name
                capacity
                owner {
                    id
                    display_name
                    style {
                        color
                    }
                    avatar_url
                }
                emotes {
                    id
                    name
                }
            }
        }
    """
    variables = {"data": {"name": name}, "user_id": user_id}
    payload = {"query": query, "variables": variables}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{ENDPOINT}/gql"
    try:
        response = requests.post(url=url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Something went wrong creating an emote set: {e}")
        sys.exit(1)
    data = response.json()
    if "errors" in data:
        print(
            f"An error occured while creating an emote set: {data['errors'][0]['message']}"
        )
        sys.exit(1)
    return data["data"]["createEmoteSet"]["id"]


def update_emote_set(token: str, name: str, capacity: int, emote_set_id: str) -> None:
    query = """
        mutation UpdateEmoteSet($id: ObjectID!, $data: UpdateEmoteSetInput!) {
            emoteSet(id: $id) {
                update(data: $data) {
                    id,
                    name
                }
            }
        }
    """
    variables = {
        "data": {"name": name, "capacity": capacity, "origins": None},
        "id": emote_set_id,
    }
    payload = {"query": query, "variables": variables}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{ENDPOINT}/gql"
    try:
        response = requests.post(url=url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Something went wrong updating emote set: {e}")
        sys.exit(1)
    data = response.json()
    if "errors" in data:
        print(
            f"An error occured while updating emote set: {data['errors'][0]['message']}"
        )
        sys.exit(1)


def is_valid_id(id: str) -> bool:
    return bool(re.compile(r"^[0-9a-fA-F]{24}$").match(id)) or id == "global"


def get_user_id_from_token() -> str:
    if "TOKEN" not in os.environ or os.environ["TOKEN"] == "":
        token = input("Your 7tv token: ")
        with open(".env", "w") as file:
            file.write(f"TOKEN={token}")
        load_dotenv()
    else:
        token = os.environ["TOKEN"]
    token_payload = json.loads(base64.b64decode(token.split(".")[1] + "=="))
    expiration_time = token_payload["exp"]
    if expiration_time < time.time():
        print("7tv token is expired")
        sys.exit(1)
    seventv_user_id = token_payload["u"]
    return seventv_user_id


def get_copied_emote_set() -> EmoteSet:
    while True:
        emote_set_id = input("What is the id of the emote set you want to copy? ")
        if is_valid_id(emote_set_id):
            from_emote_set = emote_set_from_id(emote_set_id)
            if from_emote_set is None:
                print("Emote set not found.")
            else:
                return from_emote_set
        else:
            print("Invalid id")


def get_target_user(own_seventv_id: str) -> User:
    while True:
        target_user_id = input(
            "What is the id of the user you want to copy the emote set for? Leave blank for self. "
        )
        if target_user_id == "":
            target_user_id = own_seventv_id
            target_user = user_from_id(target_user_id)
            if target_user is None:
                print("User not found.")
            else:
                if not target_user.is_subscribed():
                    print(
                        "You are not subscribed so zero-width emotes won't be copied."
                    )
                return target_user
        elif is_valid_id(target_user_id):
            target_user = user_from_id(target_user_id)
            if target_user is None:
                print("User not found.")
            elif (
                own_seventv_id not in [editor.id for editor in target_user.editors]
                and own_seventv_id != target_user_id
            ):
                print("You aren't an editor of that user.")
            else:
                if not target_user.is_subscribed():
                    print(
                        "Target user isn't subscribed so zero-width emotes won't be copied."
                    )
                return target_user
        else:
            print("Invalid id.")


def get_target_emote_set(token: str, target_user: User) -> EmoteSet:
    while True:
        target_emote_set_id = input(
            "What is the id of the emote set you want to copy into? Leave blank to create a new one. "
        )
        if target_emote_set_id == "":
            while True:
                set_name = input("What do you want to name the new emote set? ")
                if set_name != "":
                    break
                else:
                    print("Please provide a valid name for the emote set.")
            target_emote_set_id = create_emote_set(token, set_name, target_user.id)
            try:
                capacity = max(emote_set.capacity for emote_set in target_user.emote_sets)
            except ValueError:
                capacity = 600
            update_emote_set(token, set_name, capacity, target_emote_set_id)
            target_emote_set = emote_set_from_id(target_emote_set_id)
            if target_emote_set is None:
                print("Failed to find the new emote set. Try again.")
            else:
                return target_emote_set
        elif target_emote_set_id not in [
            emote_set.id for emote_set in target_user.emote_sets
        ]:
            print("User doesn't have an emote set matching the given id.")
        elif is_valid_id(target_emote_set_id):
            target_emote_set = emote_set_from_id(target_emote_set_id)
            if target_emote_set is None:
                print("Target emote set was not found.")
            else:
                return target_emote_set
        else:
            print("Invalid id.")


def copy_emotes(
    token: str, from_emote_set: EmoteSet, target_user: User, target_emote_set: EmoteSet
) -> None:
    emotes_to_be_added = [
        emote
        for emote in from_emote_set.emotes
        if not emote.data.flags.private
        and emote.name not in set(emote.name for emote in target_emote_set.emotes)
    ]
    if not target_user.is_subscribed():
        emotes_to_be_added = [
            emote for emote in emotes_to_be_added if not emote.data.flags.zero_width
        ]

    space_available = target_emote_set.capacity - target_emote_set.emote_count
    nof_emotes_to_copy = len(emotes_to_be_added)
    if space_available < nof_emotes_to_copy:
        proceed = input(
            f"The number of emotes to be added exceeds the space available in the target emote set ({nof_emotes_to_copy}>{space_available}). Some emotes won't fit. Proceed? (y/n) "
        )
        if proceed.lower() not in ["y", "yes"]:
            print("Exiting...")
            sys.exit(0)
    print(
        f"Adding {nof_emotes_to_copy} from the set '{from_emote_set.name}' ({from_emote_set.id}) to the set '{target_emote_set.name}' ({target_emote_set.id})"
    )

    for i, emote in enumerate(emotes_to_be_added, 1):
        add_emote(token, target_emote_set.id, emote.id, emote.name)
        if i % 25 == 0:
            print(f"Progress: {i}/{nof_emotes_to_copy}")
    print("All emotes successfully copied!")


def main():
    seventv_user_id = get_user_id_from_token()
    token = os.environ["TOKEN"]
    from_emote_set = get_copied_emote_set()
    target_user = get_target_user(seventv_user_id)
    target_emote_set = get_target_emote_set(token, target_user)
    copy_emotes(token, from_emote_set, target_user, target_emote_set)


if __name__ == "__main__":
    load_dotenv()
    main()
