import threading
import time
import socket
import webview
import uvicorn
from main import app

def get_free_port() -> int:
    """
    Βρίσκει μια ελεύθερη θύρα (port) στο σύστημα για να αποφύγουμε 
    συγκρούσεις αν η 8000 χρησιμοποιείται ήδη.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_server(port: int):
    """Εκκινεί τον FastAPI server."""
    # Απενεργοποιούμε τα logs για να είναι πιο "αθόρυβο" το app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == '__main__':
    # 1. Βρίσκουμε μια ελεύθερη θύρα
    port = get_free_port()
    
    # 2. Ξεκινάμε το FastAPI σε ένα ξεχωριστό background thread
    server_thread = threading.Thread(target=run_server, args=(port,))
    server_thread.daemon = True # Το thread θα κλείσει όταν κλείσει το κεντρικό πρόγραμμα
    server_thread.start()
    
    # 3. Περιμένουμε λίγο για να βεβαιωθούμε ότι ο server έχει ξεκινήσει
    time.sleep(1)
    
    # 4. Δημιουργούμε το Native Windows UI παράθυρο
    # Το width/height μπορεί να προσαρμοστεί ανάλογα με το UI σου
    window = webview.create_window(
        title="Pharos News Feed", 
        url=f"http://127.0.0.1:{port}",
        width=1200,
        height=800,
        min_size=(800, 600)
    )
    
    # 5. Εκκίνηση του παραθύρου
    webview.start()
