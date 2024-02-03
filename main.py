from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore, initialize_app, storage
from urllib.parse import unquote

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'foodhorn-9b4dc.appspot.com'
})

# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# Fuckin sort out users/posts/post_id not removing from array when deleting!!!!!!!!!!!!!!!!!
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH
# TODODODODODODODOI DWAUIODHWAUIDHWAUIHDUIAWHDUIAWH

app = Flask(__name__)

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


@app.route('/addPostToUser', methods=['POST'])
def add_post_to_user():
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

        # Query for the specific post using the post_id field
        posts = db.collection('posts').stream()

        post_found = False
        for post in posts:
            post_data = post.to_dict()
            if post_data.get('post_id') == post_id and post_data.get('creator_id') == uid:
                # Before deleting the post, delete the file from Firebase Storage

                content_url = post_data.get('content_url')
                if content_url:
                    # Extract the file path from the content_url
                    file_path = unquote(content_url.split('/o/', 1)[-1].split('?')[0])
                    file_path = file_path.replace('All%20Videos/', 'All Videos/')  # Handle URL encoding
                    # Initialize Firebase Storage
                    bucket = storage.bucket()
                    blob = bucket.blob(file_path)
                    blob.delete()

                # Delete the thumbnail file from Firebase Storage
                thumbnail_url = post_data.get('thumbnail_url')
                if thumbnail_url:
                    thumbnail_path = unquote(thumbnail_url.split('/o/', 1)[-1].split('?')[0])
                    thumbnail_path = thumbnail_path.replace('All%20Thumbnails/', 'All Thumbnails/')  # Correct directory name
                    thumbnail_blob = bucket.blob(thumbnail_path)
                    thumbnail_blob.delete()

                # Now delete the Firestore document
                post.reference.delete()
                post_found = True
                break

        if not post_found:
            return jsonify({'error': 'Post not found or unauthorized access'}), 404

        return jsonify({'message': 'Post deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 401

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5200)
