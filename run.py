from flask import Flask


app = Flask(__name__)

from routes import *
import manage_db
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    DATABASE=os.path.join(app.root_path, os.environ.get('DATABASE'))
)
manage_db.init_app(app)


if __name__ == '__main__':
    isDEBUG_MODE = os.environ.get('DEBUG')
    app.run(debug=isDEBUG_MODE)
