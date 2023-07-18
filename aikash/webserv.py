from flask import Flask, request, jsonify


class WEBkash:

    def __init__(self,
                 tree,
                 def_response):

        self.tree = tree
        self.app = Flask(__name__)

        @self.app.route('/send_message', methods=['POST'])
        def set_message():

            try:

                data = request.get_json()
                id_chat = data['id_chat']
                message = data['message']
                user = message['user']

                text = message['text']
                id_message = message['id_message']
                id_message_reply = message['reply_to_message_id']
                date = message['date']

                id_user = user['id_user']
                is_bot = user['is_bot']

                con = tree.find_context(id_chat, id_message=id_message)
                if con is None:
                    con = tree.new_context(id_chat=id_chat,
                                           id_user=id_user,
                                           id_message=id_message,
                                           reply_id_message=id_message_reply,
                                           from_bot=is_bot,
                                           text_message=text,
                                           date=date)
                else:
                    con.status = True
                    con.id_message = id_message
                    con.date = date

                con.work_context(tree, def_response)

                response = {"id_chat": con.id_chat,
                            "id_user": con.id_user,
                            "reply_to_message_id": con.reply_id_message,
                            "message": con.text_message}

                return jsonify({'response': response}), 200

            except Exception as e:
                print(str(e))
                return jsonify({'error': str(e)}), 400

    def run(self):
        self.app.run(host='0.0.0.0', port=5051)
