from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore, initialize_app, storage
from urllib.parse import unquote
from random_username.generate import generate_username
import random

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'foodhorn-9b4dc.appspot.com'
})

app = Flask(__name__)

@app.route('/fetchPosts', methods=['POST'])
def fetch_videos():
    data = request.json
    id_token = data.get('idToken')

    try:
        # Placeholder for ID token verification
        if id_token != 'H]6mI5xK7ep5*"TIKFj_':
            return jsonify({'error': "Unauthorized access."}), 401

        db = firestore.client()

        # Order posts by 'created_at' descending, then limit to 3 (or more based on your needs)
        posts_query = db.collection('posts').order_by('created_at', direction=firestore.Query.DESCENDING).limit(3)
        posts_stream = posts_query.stream()

        posts = [post.to_dict() for post in posts_stream]

        # Shuffle the posts to randomize the order
        random.shuffle(posts)

        return jsonify({
            'message': 'Posts fetched successfully',
            'posts': posts
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/verifyToken', methods=['POST'])
def verify_token():
    data = request.json
    id_token = data.get('idToken')

    try:
        # Verify the ID token while checking if the token is revoked
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        uid = decoded_token['uid']
        # Perform operations as needed with the verified UID
        return jsonify({'uid': uid}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/getUserDataFromID', methods=['POST'])
def get_user_data_from_id():
    data = request.json
    id_token = data.get('idToken')
    user_id = data.get('userId')

    try:

        # Verify the ID token and get the UID of the user
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Initialize Firestore
        db = firestore.client()

        # Reference to the user's document
        user_ref = db.collection('users').document(user_id)

        # Get the user's document
        doc = user_ref.get()

        if doc.exists:
            # If the document exists, return the user's data
            return jsonify({
                'message': 'User data fetched successfully',
                'username': doc.to_dict()['username'],
                'posts': get_users_posts(user_id)
            }), 200
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/getUserData', methods=['POST'])
def get_user_data():
    data = request.json
    id_token = data.get('idToken')
    user_id = data.get('userId')

    try:
        # Verify the ID token and get the UID of the user
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Initialize Firestore
        db = firestore.client()

        # Reference to the user's document
        user_ref = db.collection('users').document(uid)

        # Get the user's document
        doc = user_ref.get()

        if doc.exists:
            # If the document exists, return the user's data
            if user_id is None:
                return jsonify({
                    'message': 'User data fetched successfully',
                    'username': doc.to_dict()['username'],
                    'posts': get_users_posts(uid)
                }), 200
        else:
            # If the document does not exist, create one and set defaults

            username = generate_username(1)[0]

            user_ref.set({'username': username})
            return jsonify({
                'message': 'User data created successfully',
                'username': username,
                }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/updateUserData', methods=['POST'])
def update_user_data():
    data = request.json
    id_token = data.get('idToken')
    username = data.get('username')

    try:
        # Verify the ID token and get the UID of the user
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Initialize Firestore
        db = firestore.client()

        # Reference to the user's document
        user_ref = db.collection('users').document(uid)

        print("Username: ", username)

        # Update the user's document with the new data
        user_ref.update({
            'username': username
        })

        return jsonify({
            'message': 'User data updated successfully',
            'username': username
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/deletePost', methods=['POST'])
def delete_post():
    data = request.json
    id_token = data.get('idToken')
    post_id = data.get('postId')

    try:

        # Verify the ID token and get the UID of the user
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Initialize Firestore
        db = firestore.client()

        # Reference to the user's document
        user_ref = db.collection('users').document(uid)
        post_ref = db.collection('posts').document(post_id)

        for post in user_ref.get().to_dict()['posts']:
            if post == post_id:
                user_ref.update({
                    'posts': firestore.ArrayRemove([post_id])
                })

                content_url = post_ref.get().to_dict()['content_url']
                thumbnail_url = post_ref.get().to_dict()['thumbnail_url']

                if content_url:
                    file_path = unquote(content_url.split('/o/', 1)[-1].split('?')[0])
                    file_path = file_path.replace('All%20Videos/', 'All Videos/')
                    bucket = storage.bucket()
                    blob = bucket.blob(file_path)
                    blob.delete()
                
                if thumbnail_url:
                    thumbnail_path = unquote(thumbnail_url.split('/o/', 1)[-1].split('?')[0])
                    thumbnail_path = thumbnail_path.replace('All%20Thumbnails/', 'All Thumbnails/')
                    thumbnail_blob = bucket.blob(thumbnail_path)
                    thumbnail_blob.delete()

                post_ref.delete()
                return jsonify({'message': 'Post removed from user successfully'}), 200

        return jsonify({'error': 'Post not found or unauthorized access'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/addPost', methods=['POST'])
def add_post_to_user():
    data = request.json
    id_token = data.get('idToken')
    post_data = data.get('post')

    try:
        # Verify the ID token and get the UID of the user
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Initialize Firestore
        db = firestore.client()

        # Create a new document reference with an auto-generated ID in the 'posts' collection
        post_ref = db.collection('posts').document()
        post_id = post_ref.id  # Get the auto-generated ID


        # Set the post data to the new document
        post_ref.set(post_data)

        post_ref.update({
            'post_id': post_id,
        })

        # Reference to the user's document
        user_ref = db.collection('users').document(uid)

        # Run a transaction to ensure atomicity
        @firestore.transactional
        def update_user(transaction, user_ref, post_id):
            snapshot = user_ref.get(transaction=transaction)
            if snapshot.exists:
                transaction.update(user_ref, {
                    'posts': firestore.ArrayUnion([post_id])
                })
            else:
                # If the user does not exist, create the user with the post
                transaction.set(user_ref, {
                    'posts': [post_id]
                })

        # Start the transaction
        transaction = db.transaction()
        update_user(transaction, user_ref, post_id)

        return jsonify({'message': 'Post added to user successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 401

def get_users_posts(uid):

    posts = []

    # Initialize Firestore
    db = firestore.client()

    # Reference to the user's document
    user_ref = db.collection('users').document(uid)
    # get lists in posts
    post_list = user_ref.get().to_dict()['posts']
    for post in post_list:
        post_ref = db.collection('posts').document(post)
        posts.append(post_ref.get().to_dict())

    return posts

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5200)
