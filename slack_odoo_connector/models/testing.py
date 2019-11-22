user_id = {
    "ok": 'true',
    "user": {
        "id": "ULKU10V29",
        "team_id": "TLLJCMQHL",
        "name": "shahrukh2641",
        "deleted": 'false',
        "color": "3c989f",
        "real_name": "Jack Smith",
        "tz": "Asia\/Karachi",
        "tz_label": "Pakistan Standard Time",
        "tz_offset": 18000,
        "profile": {
            "title": "",
            "phone": "",
            "skype": "",
            "real_name": "Jack Smith",
            "real_name_normalized": "Jack Smith",
            "display_name": "Jack Smith",
            "display_name_normalized": "Jack Smith",
            "fields": 'null',
            "status_text": "",
            "status_emoji": "",
            "status_expiration": 0,
            "avatar_hash": "g83371c40f7d",
            "email": "shahrukh2641@gmail.com",
            "image_24": "https:\/\/secure.gravatar.com\/avatar\/83371c40f7d37c78d4453571a8db1fa9.jpg?s=24&d=https%3A%2F%2Fa.slack-edge.com%2F136bc%2Fimg%2Favatars%2Fuser_shapes%2Fava_0025-24.png",
            "image_32": "https:\/\/secure.gravatar.com\/avatar\/83371c40f7d37c78d4453571a8db1fa9.jpg?s=32&d=https%3A%2F%2Fa.slack-edge.com%2F136bc%2Fimg%2Favatars%2Fuser_shapes%2Fava_0025-32.png",
            "image_48": "https:\/\/secure.gravatar.com\/avatar\/83371c40f7d37c78d4453571a8db1fa9.jpg?s=48&d=https%3A%2F%2Fa.slack-edge.com%2F136bc%2Fimg%2Favatars%2Fuser_shapes%2Fava_0025-48.png",
            "image_72": "https:\/\/secure.gravatar.com\/avatar\/83371c40f7d37c78d4453571a8db1fa9.jpg?s=72&d=https%3A%2F%2Fa.slack-edge.com%2F136bc%2Fimg%2Favatars%2Fuser_shapes%2Fava_0025-72.png",
            "image_192": "https:\/\/secure.gravatar.com\/avatar\/83371c40f7d37c78d4453571a8db1fa9.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2F70dae%2Fimg%2Favatars%2Fuser_shapes%2Fava_0025-192.png%7EHEAD",
            "image_512": "https:\/\/secure.gravatar.com\/avatar\/83371c40f7d37c78d4453571a8db1fa9.jpg?s=512&d=https%3A%2F%2Fa.slack-edge.com%2F136bc%2Fimg%2Favatars%2Fuser_shapes%2Fava_0025-512.png",
            "status_text_canonical": "",
            "team": "TLLJCMQHL"
        },
        "is_admin": 'false',
        "is_owner": 'false',
        "is_primary_owner": 'false',
        "is_restricted": 'false',
        "is_ultra_restricted": 'false',
        "is_bot": 'false',
        "is_app_user": 'false',
        "updated": 1563543216,
        "has_2fa": 'false'
    }
}

to_email = None

if "user" in user_id:
    data = user_id['user']['profile']
    print(data)
