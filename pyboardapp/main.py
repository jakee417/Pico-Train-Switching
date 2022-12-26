from app.connect import connect
import app.tinyweb_server as tinyweb_server

if __name__ == "__main__":
    connect()
    tinyweb_server.run()
    