from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

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

@app.route('/deletePost', methods=['POST'])
def delete_post():
    data = request.json
    id_token = data.get('idToken')
    post_id = data.get('postId')

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        db = firestore.client()
        post_ref = db.collection('posts').document(post_id)
        post = post_ref.get()
        if post.exists:
            post_data = post.to_dict()
            if post_data['creator_id'] != uid:
                return jsonify({'error': 'Unauthorized'}), 401
            post_ref.delete()
        else:
            return jsonify({'error': 'Post not found'}), 404

        return jsonify({'message': 'Post deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5200)
