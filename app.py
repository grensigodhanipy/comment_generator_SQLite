from flask import Flask, request, jsonify
import google.generativeai as genai
import sqlite3
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

genai.configure(api_key='AIzaSyAO2ohK36Fc-DV_Ryi1q1CU-aFxQmoA0tw')

DATABASE = 'custom_options.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS custom_options
                    (label TEXT PRIMARY KEY, prompt TEXT)''')
    conn.commit()
    conn.close()

def load_custom_options():
    conn = get_db_connection()
    options = {row['label']: row['prompt'] for row in conn.execute('SELECT * FROM custom_options')}
    conn.close()
    return options

def save_custom_option(label, prompt):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO custom_options (label, prompt) VALUES (?, ?)',
                 (label, prompt))
    conn.commit()
    conn.close()

def remove_custom_option(label):
    conn = get_db_connection()
    conn.execute('DELETE FROM custom_options WHERE label = ?', (label,))
    conn.commit()
    conn.close()

def generate_comment(post_content, style, custom_prompt=None):
    if custom_prompt:
        prompt = f"{custom_prompt}: {post_content}"
    elif style == "neutral":
        prompt = f"Be a calm and composed LinkedIn business coach. Respond to this LinkedIn post with a comment that conveys a neutral perspective. Make sure not to repeat what has already been said in the post. Use new words, phrases, ideas and insights. Do not include any hashtags and emoji. Keep it less than 15 words: {post_content}"
    elif style == "new insight":
        prompt = f"The above is a post on LinkedIn. I want to be an authoritative and insightful LinkedIn user who is friendly in response to the post. Write and add brand new insights in response to the post and make sure not to repeat what has already been said in the post. Use new words, phrases, ideas and insights. Keep it short and professional: {post_content}"
    else:
        prompt = f"Write a {style} comment about this LinkedIn post: {post_content}"

    try:
        response = genai.generate_text(prompt=prompt, temperature=0.7)
        if hasattr(response, 'candidates'):
            candidates = response.candidates
            if candidates:
                first_candidate = candidates[0]
                output_text = first_candidate.get('output', "Error: No output found in the API response.")
            else:
                output_text = "Error: No output from the API."
        else:
            output_text = "Error: No candidates found in the API response."
    except Exception as e:
        output_text = f"Error generating comment: {str(e)}"

    return output_text

@app.route('/generate_comment', methods=['POST'])
def generate_comment_endpoint():
    try:
        data = request.json
        post_content = data.get('postContent', '')
        style = data.get('style', '')
        custom_options = load_custom_options()

        if post_content and style:
            if style in custom_options:
                custom_prompt = custom_options[style]
                generated_comment = generate_comment(post_content, style, custom_prompt=custom_prompt)
            else:
                generated_comment = generate_comment(post_content, style)
            return jsonify({'generated_comment': generated_comment})
        else:
            return jsonify({'error': 'Invalid input'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/add_custom_option', methods=['POST'])
def add_custom_option():
    try:
        data = request.json
        label = data.get('label', '')
        prompt = data.get('prompt', '')
        if label and prompt:
            save_custom_option(label, prompt)
            return jsonify({'message': 'Custom option added successfully'})
        else:
            return jsonify({'error': 'Invalid input'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/get_custom_options', methods=['GET'])
def get_custom_options():
    try:
        options = load_custom_options()
        return jsonify(options)
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/remove_custom_option', methods=['POST'])
def remove_custom_option_endpoint():
    try:
        data = request.json
        label = data.get('label', '')
        if label:
            remove_custom_option(label)
            return jsonify({'message': 'Custom option removed successfully'})
        else:
            return jsonify({'error': 'Invalid input'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)