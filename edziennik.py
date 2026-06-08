import wx
import wx.grid as grid
import requests

API = "http://192.168.56.1:10000"  # ⚠ MUSI pasować do backendu PRO

token = None
user = None


# ================= API =================

def headers():
    return {"Authorization": token} if token else {}


def api_get(path):
    try:
        return requests.get(API + path, headers=headers(), timeout=4)
    except:
        wx.MessageBox("Brak połączenia z API")
        return None


def api_post(path, data):
    try:
        return requests.post(API + path, json=data, headers=headers(), timeout=4)
    except:
        wx.MessageBox("Brak połączenia z API")
        return None


# ================= LOGIN =================

class LoginFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="LOGIN", size=(350, 250))

        panel = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)

        v.Add(wx.StaticText(panel, label="Login"))
        self.login_input = wx.TextCtrl(panel)
        v.Add(self.login_input, 0, wx.EXPAND | wx.ALL, 5)

        v.Add(wx.StaticText(panel, label="Hasło"))
        self.pass_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        v.Add(self.pass_input, 0, wx.EXPAND | wx.ALL, 5)

        btn = wx.Button(panel, label="Zaloguj")
        btn.Bind(wx.EVT_BUTTON, self.on_login)
        v.Add(btn, 0, wx.ALL | wx.CENTER, 10)

        panel.SetSizer(v)

    def on_login(self, event):
        global token, user

        r = api_post("/login", {
            "login": self.login_input.GetValue(),
            "password": self.pass_input.GetValue()
        })

        if not r or r.status_code != 200:
            wx.MessageBox("Błąd logowania")
            return

        data = r.json()

        # 🔥 FIX PRO BACKEND
        token = data["access"]
        user = data["user"]

        MainFrame().Show()
        self.Destroy()


# ================= MAIN =================

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="DZIENNIK PRO FIX", size=(1100, 700))

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.HORIZONTAL)

        menu = wx.BoxSizer(wx.VERTICAL)

        menu.Add(wx.StaticText(panel, label=f"{user['login']} ({user['role']})"), 0, wx.ALL, 5)

        buttons = [
            ("Dashboard", self.dashboard),
            ("Oceny", self.grades),
            ("Frekwencja", self.attendance),
            ("Wiadomości", self.messages),
            ("Użytkownicy", self.users),
            ("Wyloguj", self.logout),
        ]

        for name, fn in buttons:
            b = wx.Button(panel, label=name)
            b.Bind(wx.EVT_BUTTON, fn)
            menu.Add(b, 0, wx.EXPAND | wx.ALL, 3)

        root.Add(menu, 0, wx.EXPAND | wx.ALL, 10)

        self.content = wx.Panel(panel)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.content.SetSizer(self.sizer)

        root.Add(self.content, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)

        self.dashboard(None)

    # ================= CLEAR =================

    def clear(self):
        self.sizer.Clear(True)
        self.content.Layout()

    # ================= DASHBOARD =================

    def dashboard(self, e):
        self.clear()

        txt = f"""
SYSTEM OK

User: {user['login']}
Role: {user['role']}
API: {API}
"""

        self.sizer.Add(wx.StaticText(self.content, label=txt), 0, wx.ALL, 10)
        self.Layout()

    # ================= GRADES =================

    def grades(self, e):
        self.clear()

        r = api_get(f"/grades/{user['id']}")
        if not r:
            return

        data = r.json()

        g = grid.Grid(self.content)
        g.CreateGrid(max(len(data), 1), 3)

        g.SetColLabelValue(0, "ID")
        g.SetColLabelValue(1, "Przedmiot")
        g.SetColLabelValue(2, "Ocena")

        for i, x in enumerate(data):
            g.SetCellValue(i, 0, str(x["id"]))
            g.SetCellValue(i, 1, x["subject"])
            g.SetCellValue(i, 2, x["value"])

        self.sizer.Add(g, 1, wx.EXPAND)
        self.Layout()

    # ================= ATTENDANCE =================

    def attendance(self, e):
        self.clear()

        r = api_get(f"/attendance/{user['id']}")
        if not r:
            return

        data = r.json()

        g = grid.Grid(self.content)
        g.CreateGrid(max(len(data), 1), 2)

        g.SetColLabelValue(0, "ID")
        g.SetColLabelValue(1, "Status")

        for i, x in enumerate(data):
            g.SetCellValue(i, 0, str(x["id"]))
            g.SetCellValue(i, 1, x["status"])

        self.sizer.Add(g, 1, wx.EXPAND)
        self.Layout()

    # ================= MESSAGES =================

    def messages(self, e):
        self.clear()

        r = api_get(f"/messages/{user['id']}")
        if not r:
            return

        box = wx.TextCtrl(self.content, style=wx.TE_MULTILINE)

        for m in r.json():
            box.AppendText(f"{m['sender']} -> {m['receiver']}\n{m['text']}\n\n")

        self.sizer.Add(box, 1, wx.EXPAND)
        self.Layout()

    # ================= USERS =================

    def users(self, e):
        self.clear()

        if user["role"] != "ADMIN":
            self.sizer.Add(wx.StaticText(self.content, label="Brak dostępu"))
            self.Layout()
            return

        r = api_get("/users")
        if not r:
            return

        data = r.json()

        g = grid.Grid(self.content)
        g.CreateGrid(max(len(data), 1), 3)

        g.SetColLabelValue(0, "ID")
        g.SetColLabelValue(1, "Login")
        g.SetColLabelValue(2, "Rola")

        for i, x in enumerate(data):
            g.SetCellValue(i, 0, str(x["id"]))
            g.SetCellValue(i, 1, x["login"])
            g.SetCellValue(i, 2, x["role"])

        self.sizer.Add(g, 1, wx.EXPAND)
        self.Layout()

    # ================= LOGOUT =================

    def logout(self, e):
        global token, user
        token = None
        user = None

        LoginFrame().Show()
        self.Destroy()


# ================= START =================

if __name__ == "__main__":
    app = wx.App()
    LoginFrame().Show()
    app.MainLoop()