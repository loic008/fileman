import os
import sys
import json
import sqlite3
import hashlib
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeView, QFileSystemModel,
                             QTabWidget, QVBoxLayout, QWidget, QLabel, QMenu,
                             QAction, QAbstractItemView, QHeaderView, QMessageBox,
                             QDialog, QLineEdit, QPushButton, QFormLayout, QDialogButtonBox,
                             QInputDialog, QHBoxLayout, QSplitter, QTextEdit, QStatusBar,
                             QFileDialog, QGridLayout, QToolBar, QComboBox, QGroupBox,
                             QSizePolicy, QFrame, QScrollArea, QTextEdit, QCalendarWidget)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QModelIndex, QDir, QSize, QSettings, QDate

# Database initialization
def init_db():
    conn = sqlite3.connect('file_tree_manager.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Projects table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        master_path TEXT NOT NULL,
        client_name TEXT NOT NULL,
        delivery_path TEXT NOT NULL,
        project_comment TEXT DEFAULT '',
        delivery_date TEXT DEFAULT '',
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )
    ''')
    
    # File attributes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS file_attributes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        publish_status BOOLEAN DEFAULT FALSE,
        to_client_status BOOLEAN DEFAULT FALSE,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        UNIQUE(project_id, file_path)
    )
    ''')
    
    # Default admin user if not exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                      ("admin", password_hash))
    
    # Create a default project if none exists
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        # Create default directories
        home_dir = QDir.homePath()
        default_master = os.path.join(home_dir, "FileTreeManager", "DefaultProject")
        default_delivery = os.path.join(home_dir, "FileTreeManager", "Deliveries")
        
        os.makedirs(default_master, exist_ok=True)
        os.makedirs(default_delivery, exist_ok=True)
        
        # Add a sample file
        with open(os.path.join(default_master, "sample.txt"), "w") as f:
            f.write("This is a sample file for the default project.")
        
        cursor.execute(
            "INSERT INTO projects (name, master_path, client_name, delivery_path, created_by) VALUES (?, ?, ?, ?, ?)",
            ("Default Project", default_master, "Default Client", default_delivery, 1)
        )
    
    conn.commit()
    conn.close()

# Initialize database on import
init_db()

class LoginWindow(QDialog):
    """Login window for user authentication"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Publish Manager - Login")
        self.setFixedSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("PUBLISH MANAGER")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        self.username_combo = QComboBox()
        self.username_combo.setEditable(False)
        self.username_combo.setMinimumHeight(35)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(35)
        self.password.setPlaceholderText("Enter your password")
        
        form_layout.addRow("Username:", self.username_combo)
        form_layout.addRow("Password:", self.password)
        
        layout.addLayout(form_layout)
        
        # Load users into combo box
        self.load_users()
        
        # Buttons
        button_layout = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.authenticate)
        login_btn.setMinimumHeight(30)
        
        cancel_btn = QPushButton("Exit")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(30)
        
        button_layout.addWidget(login_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Footer
        footer = QLabel("© 2025 PORTEUR.inc")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
        
        self.setLayout(layout)
        
    def load_users(self):
        """Load available users into the combo box"""
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER by username")
        users = cursor.fetchall()
        conn.close()
        
        self.username_combo.clear()
        for user in users:
            self.username_combo.addItem(user[0])
        
    def authenticate(self):
        username = self.username_combo.currentText()
        password = self.password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
            
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", 
                     (username, password_hash))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.user_id = user[0]
            self.username_str = username
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Invalid password")

class UserManagerDialog(QDialog):
    """Dialog for user management"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Management")
        self.setFixedSize(400, 800)
        self.setup_ui()
        self.load_users()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Account management group
        account_group = QGroupBox("Account Management")
        account_layout = QVBoxLayout()
        account_layout.setSpacing(15)
        account_layout.setContentsMargins(15, 20, 15, 15)
        
        self.user_combo = QComboBox()
        self.user_combo.setMinimumHeight(35)
        self.user_combo.currentTextChanged.connect(self.on_user_selected)
        account_layout.addWidget(QLabel("Select User:"))
        account_layout.addWidget(self.user_combo)
        
        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("New username")
        self.new_username.setMinimumHeight(35)
        account_layout.addWidget(QLabel("New Username:"))
        account_layout.addWidget(self.new_username)
        
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("New password")
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setMinimumHeight(35)
        account_layout.addWidget(QLabel("New Password:"))
        account_layout.addWidget(self.new_password)
        
        update_btn = QPushButton("Update Account")
        update_btn.clicked.connect(self.update_account)
        update_btn.setMinimumHeight(35)
        account_layout.addWidget(update_btn)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # New user group
        new_user_group = QGroupBox("Create New User")
        new_user_layout = QVBoxLayout()
        new_user_layout.setSpacing(15)
        new_user_layout.setContentsMargins(15, 20, 15, 15)
        
        self.new_user_name = QLineEdit()
        self.new_user_name.setPlaceholderText("Username")
        self.new_user_name.setMinimumHeight(35)
        new_user_layout.addWidget(QLabel("Username:"))
        new_user_layout.addWidget(self.new_user_name)
        
        self.new_user_password = QLineEdit()
        self.new_user_password.setPlaceholderText("Password")
        self.new_user_password.setEchoMode(QLineEdit.Password)
        self.new_user_password.setMinimumHeight(35)
        new_user_layout.addWidget(QLabel("Password:"))
        new_user_layout.addWidget(self.new_user_password)
        
        create_btn = QPushButton("Create User")
        create_btn.clicked.connect(self.create_user)
        create_btn.setMinimumHeight(35)
        new_user_layout.addWidget(create_btn)
        
        new_user_group.setLayout(new_user_layout)
        layout.addWidget(new_user_group)
        
        # Remove user group
        remove_group = QGroupBox("Remove User")
        remove_layout = QVBoxLayout()
        remove_layout.setSpacing(15)
        remove_layout.setContentsMargins(15, 20, 15, 15)
        
        self.remove_user_combo = QComboBox()
        self.remove_user_combo.setMinimumHeight(35)
        remove_layout.addWidget(QLabel("Select User to Remove:"))
        remove_layout.addWidget(self.remove_user_combo)
        
        remove_btn = QPushButton("Remove User")
        remove_btn.clicked.connect(self.remove_user)
        remove_btn.setMinimumHeight(35)
        remove_layout.addWidget(remove_btn)
        
        remove_group.setLayout(remove_layout)
        layout.addWidget(remove_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(35)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
    def load_users(self):
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER by username")
        users = cursor.fetchall()
        conn.close()
        
        self.user_combo.clear()
        self.remove_user_combo.clear()
        for user in users:
            self.user_combo.addItem(user[0])
            if user[0] != "admin":  # Don't add admin to remove list
                self.remove_user_combo.addItem(user[0])
            
    def on_user_selected(self, username):
        self.new_username.setText(username)
        self.new_password.clear()
        
    def update_account(self):
        old_username = self.user_combo.currentText()
        new_username = self.new_username.text()
        new_password = self.new_password.text()
        
        if not new_username:
            QMessageBox.warning(self, "Error", "Please enter a username")
            return
            
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        
        if new_password:
            password_hash = hashlib.sha256(new_password.encode()).hexdigest())
            cursor.execute("UPDATE users SET username = ?, password_hash = ? WHERE username = ?",
                         (new_username, password_hash, old_username))
        else:
            cursor.execute("UPDATE users SET username = ? WHERE username = ?",
                         (new_username, old_username))
            
        conn.commit()
        conn.close()
        
        self.load_users()
        QMessageBox.information(self, "Success", "Account updated successfully")
        
    def create_user(self):
        username = self.new_user_name.text()
        password = self.new_user_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
            
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                         (username, password_hash))
            conn.commit()
            QMessageBox.information(self, "Success", "User created successfully")
            self.new_user_name.clear()
            self.new_user_password.clear()
            self.load_users()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Username already exists")
        finally:
            conn.close()
            
    def remove_user(self):
        username = self.remove_user_combo.currentText()
        
        if username == "admin":
            QMessageBox.warning(self, "Error", "Cannot remove admin user")
            return
            
        reply = QMessageBox.question(self, "Confirm Removal", 
                                   f"Are you sure you want to remove user '{username}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect('file_tree_manager.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            
            self.load_users()
            QMessageBox.information(self, "Success", "User removed successfully")

class NewProjectDialog(QDialog):
    """Dialog for creating a new project"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setFixedSize(500, 550)  # Reduced height since we removed delivery path
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Project details group
        details_group = QGroupBox("Project Details")
        details_layout = QFormLayout()
        details_layout.setSpacing(10)
        
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("Enter project name")
        self.project_name.setMinimumHeight(30)
        details_layout.addRow("Project Name:", self.project_name)
        
        self.client_name = QLineEdit()
        self.client_name.setPlaceholderText("Enter client name")
        self.client_name.setMinimumHeight(30)
        details_layout.addRow("Client Name:", self.client_name)
        
        self.project_comment = QLineEdit()
        self.project_comment.setPlaceholderText("Enter project comment")
        self.project_comment.setMinimumHeight(30)
        details_layout.addRow("Comment:", self.project_comment)
        
        self.delivery_date = QLineEdit()
        self.delivery_date.setPlaceholderText("YYYY-MM-DD")
        self.delivery_date.setMinimumHeight(30)
        details_layout.addRow("Delivery Date:", self.delivery_date)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Paths group
        paths_group = QGroupBox("Project Paths")
        paths_layout = QVBoxLayout()
        paths_layout.setSpacing(10)
        
        # Master path selection
        master_layout = QHBoxLayout()
        self.master_path = QLineEdit()
        self.master_path.setPlaceholderText("Select master directory")
        self.master_path.setMinimumHeight(30)
        master_btn = QPushButton("Browse")
        master_btn.clicked.connect(self.select_master_path)
        master_btn.setMinimumHeight(30)
        master_btn.setMinimumWidth(70)
        master_layout.addWidget(self.master_path)
        master_layout.addWidget(master_btn)
        paths_layout.addWidget(QLabel("Master Directory:"))
        paths_layout.addLayout(master_layout)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton("Create Project")
        create_btn.clicked.connect(self.accept)
        create_btn.setMinimumHeight(35)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def select_master_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Master Directory")
        if path:
            self.master_path.setText(path)
            
    def get_project_data(self):
        return {
            "name": self.project_name.text(),
            "master_path": self.master_path.text(),
            "client_name": self.client_name.text(),
            "comment": self.project_comment.text(),
            "delivery_date": self.delivery_date.text()
        }


class AttributeManager:
    """Manages publish/to_client attributes and history tracking"""
    def __init__(self, master_path):
        self.master_path = master_path
    
    def get_sidecar_path(self, path):
        """Get path for sidecar JSON file"""
        return f"{path}.attr.json"
    
    def load_data(self, path):
        """Load attribute data from sidecar file"""
        sidecar_path = self.get_sidecar_path(path)
        if os.path.exists(sidecar_path):
            try:
                with open(sidecar_path, 'r') as f:
                    return json.load(f)
            except:
                return {"publish": [], "to_client": []}
        return {"publish": [], "to_client": []}
    
    def save_data(self, path, data):
        """Save attribute data to sidecar file"""
        sidecar_path = self.get_sidecar_path(path)
        with open(sidecar_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def update_attribute(self, path, attribute, value, user):
        """Update attribute with timestamp history"""
        data = self.load_data(path)
        
        timestamp = datetime.now().isoformat()
        data[attribute].append({
            "status": value,
            "timestamp": timestamp,
            "user": user
        })
        
        self.save_data(path, data)
        
        # Update centralized database
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        
        # Get project ID from master path
        cursor.execute("SELECT id FROM projects WHERE master_path = ?", (self.master_path,))
        project_result = cursor.fetchone()
        
        if project_result:
            project_id = project_result[0]
            rel_path = os.path.relpath(path, self.master_path)
            
            # Check if file exists in database
            cursor.execute('''
            SELECT COUNT(*) FROM file_attributes 
            WHERE project_id = ? AND file_path = ?
            ''', (project_id, rel_path))
            
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                INSERT INTO file_attributes 
                (project_id, file_path, publish_status, to_client_status) 
                VALUES (?, ?, ?, ?)
                ''', (project_id, rel_path, False, False))
            
            # Update the attribute
            if attribute == "publish":
                cursor.execute('''
                UPDATE file_attributes SET publish_status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE file_path = ? AND project_id = ?
                ''', (value, rel_path, project_id))
            elif attribute == "to_client":
                cursor.execute('''
                UPDATE file_attributes SET to_client_status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE file_path = ? AND project_id = ?
                ''', (value, rel_path, project_id))
                
        conn.commit()
        conn.close()
        
        return timestamp
    
    def get_current_status(self, path, attribute):
        """Get current status and timestamp for an attribute"""
        data = self.load_data(path)
        if data[attribute]:
            last_entry = data[attribute][-1]
            return last_entry["status"], last_entry["timestamp"], last_entry.get("user", "Unknown")
        return False, "", "Unknown"
    
    def get_attribute_history(self, path, attribute):
        """Get complete history of an attribute"""
        data = self.load_data(path)
        return data.get(attribute, [])


class FileSystemModelWithBadges(QFileSystemModel):
    """Custom file system model that displays attribute badges and hides .json files"""
    def __init__(self, attribute_manager):
        super().__init__()
        self.attribute_manager = attribute_manager
        
    def columnCount(self, parent=QModelIndex()):
        return super().columnCount(parent) + 1  # Add one extra column for status
        
    def data(self, index, role=Qt.DisplayRole):
        # For the new status column (column 4)
        if index.column() == 4 and role == Qt.DisplayRole:
            path = self.filePath(self.index(index.row(), 0, index.parent()))
            if path.endswith('.json'):
                return None
                
            # Get attribute status
            publish_status, _, _ = self.attribute_manager.get_current_status(path, "publish")
            client_status, _, _ = self.attribute_manager.get_current_status(path, "to_client")
            
            # Create status text
            status = []
            if publish_status:
                status.append("Published")
            if client_status:
                status.append("To Client")
                
            return " | ".join(status) if status else "No Status"
            
        if index.column() == 0 and role == Qt.DisplayRole:
            path = self.filePath(index)
            
            # Skip .json files
            if path.endswith('.json'):
                return None
                
            return super().data(index, role)
            
        return super().data(index, role)
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 4:  # Our new status column
                return "Status"
            elif section == 0:
                return "Name"
            elif section == 1:
                return "Size"
            elif section == 2:
                return "Type"
            elif section == 3:
                return "Date Modified"
        return super().headerData(section, orientation, role)


class ProjectTab(QWidget):
    """Represents a project tab with file tree and attributes"""
    def __init__(self, project_id, project_name, master_path, client_name, delivery_path, username, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_name = project_name
        self.master_path = master_path
        self.client_name = client_name
        self.delivery_path = delivery_path
        self.username = username
        self.attribute_manager = AttributeManager(master_path)
        self.settings = QSettings("FileTreeManager", "ProjectState")
        
        # Load project details from database
        self.load_project_details()
        
        # Setup UI
        self.setup_ui()
        
        # Restore tree state
        self.restore_tree_state()
        
    def load_project_details(self):
        """Load project details from database"""
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        cursor.execute("SELECT project_comment, delivery_date FROM projects WHERE id = ?", (self.project_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            self.project_comment = result[0] or ""
            self.delivery_date = result[1] or ""
        else:
            self.project_comment = ""
            self.delivery_date = ""
    
    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Section 1: File Tree with scaling control
        tree_container = QWidget()
        tree_container_layout = QVBoxLayout()
        tree_container_layout.setContentsMargins(0, 0, 0, 0)
        tree_container_layout.setSpacing(0)
        
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Box)
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(5, 5, 5, 5)
        
        tree_label = QLabel("Files")
        tree_label.setFont(QFont("Arial", 12, QFont.Bold))
        tree_layout.addWidget(tree_label)
        
        # Tree view setup
        self.tree_view = QTreeView()
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.expanded.connect(self.save_tree_state)
        self.tree_view.collapsed.connect(self.save_tree_state)
        
        # File system model with badges
        self.file_model = FileSystemModelWithBadges(self.attribute_manager)
        self.file_model.setRootPath(self.master_path)
        self.file_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(self.master_path))
        
        # Show the status column and hide unnecessary columns
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setColumnWidth(0, 300)  # Name column width
        self.tree_view.setColumnWidth(4, 150)  # Status column width
        self.tree_view.hideColumn(1)  # Size
        self.tree_view.hideColumn(2)  # Type
        self.tree_view.hideColumn(3)  # Modified
        
        tree_layout.addWidget(self.tree_view)
        tree_frame.setLayout(tree_layout)
        tree_container_layout.addWidget(tree_frame)
        
        # Scaling control at the bottom
        scaling_frame = QFrame()
        scaling_frame.setMaximumHeight(40)
        scaling_layout = QHBoxLayout()
        scaling_layout.setContentsMargins(5, 5, 5, 5)
        
        scaling_label = QLabel("Scaling:")
        scaling_layout.addWidget(scaling_label)
        
        self.scaling_combo = QComboBox()
        self.scaling_combo.addItems(["100%", "125%", "150%"])
        self.scaling_combo.setCurrentText("100%")
        self.scaling_combo.currentTextChanged.connect(self.change_scaling)
        self.scaling_combo.setMaximumWidth(100)
        scaling_layout.addWidget(self.scaling_combo)
        scaling_layout.addStretch()
        
        scaling_frame.setLayout(scaling_layout)
        tree_container_layout.addWidget(scaling_frame)
        
        tree_container.setLayout(tree_container_layout)
        
        # Section 2: Details
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.Box)
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create vertical splitter for details section
        details_splitter = QSplitter(Qt.Vertical)
        details_splitter.setObjectName("details_splitter")
        
        # File details panel
        file_details_widget = QWidget()
        file_details_layout = QVBoxLayout()
        file_details_layout.setContentsMargins(0, 0, 0, 0)
        
        details_label = QLabel("File Details")
        details_label.setFont(QFont("Arial", 12, QFont.Bold))
        file_details_layout.addWidget(details_label)
        
        self.details_panel = QTextEdit()
        self.details_panel.setReadOnly(True)
        file_details_layout.addWidget(self.details_panel)
        
        file_details_widget.setLayout(file_details_layout)
        
        # Project info panel (smaller portion)
        project_info_widget = QWidget()
        project_info_layout = QVBoxLayout()
        project_info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        project_info_layout.addWidget(divider)
        
        # Project info
        project_info_label = QLabel("Project Information")
        project_info_label.setFont(QFont("Arial", 12, QFont.Bold))
        project_info_layout.addWidget(project_info_label)
        
        # Project name (editable)
        self.project_name_edit = QLineEdit(self.project_name)
        self.project_name_edit.setFont(QFont("Arial", 16))
        self.project_name_edit.editingFinished.connect(self.update_project_name)
        project_info_layout.addWidget(self.project_name_edit)
        
        # Project comment (editable) - changed to QTextEdit
        project_info_layout.addWidget(QLabel("Comment:"))
        self.project_comment_edit = QTextEdit(self.project_comment)
        self.project_comment_edit.setPlaceholderText("Add project details...")
        self.project_comment_edit.textChanged.connect(self.update_project_comment)
        self.project_comment_edit.setMaximumHeight(100)  # Limit height for better UI
        project_info_layout.addWidget(self.project_comment_edit)
        
        # Delivery date (editable with calendar)
        project_info_layout.addWidget(QLabel("Delivery Date:"))
        date_layout = QHBoxLayout()
        
        self.delivery_date_edit = QLineEdit(self.delivery_date)
        self.delivery_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.delivery_date_edit.textChanged.connect(self.update_delivery_date)
        date_layout.addWidget(self.delivery_date_edit)
        
        calendar_btn = QPushButton("📅")
        calendar_btn.setMaximumWidth(30)
        calendar_btn.clicked.connect(self.show_calendar)
        date_layout.addWidget(calendar_btn)
        
        project_info_layout.addLayout(date_layout)
        
        # Client info
        client_label = QLabel(f"Client: {self.client_name}")
        client_label.setFont(QFont("Arial", 10))
        project_info_layout.addWidget(client_label)
        
        # Path buttons
        path_layout = QHBoxLayout()
        
        master_btn = QPushButton("Project Path")
        master_btn.clicked.connect(lambda: self.show_path(self.master_path))
        master_btn.setMinimumHeight(25)
        path_layout.addWidget(master_btn)
        
        delivery_btn = QPushButton("Delivery Path")
        delivery_btn.clicked.connect(lambda: self.show_path(self.delivery_path))
        delivery_btn.setMinimumHeight(25)
        path_layout.addWidget(delivery_btn)
        
        project_info_layout.addLayout(path_layout)
        
        project_info_widget.setLayout(project_info_layout)
        
        # Add to details splitter
        details_splitter.addWidget(file_details_widget)
        details_splitter.addWidget(project_info_widget)
        
        # Restore splitter state
        details_splitter_state = self.settings.value(f"details_splitter_{self.project_id}")
        if details_splitter_state:
            details_splitter.restoreState(details_splitter_state)
        else:
            details_splitter.setSizes([300, 150])  # Adjusted size for more project info
        
        details_layout.addWidget(details_splitter)
        details_frame.setLayout(details_layout)
        
        # Add sections to main splitter
        main_splitter.addWidget(tree_container)
        main_splitter.addWidget(details_frame)
        
        # Restore main splitter state
        splitter_state = self.settings.value(f"main_splitter_{self.project_id}")
        if splitter_state:
            main_splitter.restoreState(splitter_state)
        else:
            main_splitter.setSizes([600, 400])
        
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
    
    def change_scaling(self, scale_text):
        """Change the scaling of the file tree"""
        scale_factor = int(scale_text.replace('%', '')) / 100.0
        font = self.tree_view.font()
        base_size = 9  # Base font size
        font.setPointSize(int(base_size * scale_factor))
        self.tree_view.setFont(font)
    
    def show_calendar(self):
        """Show calendar dialog for date selection"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Delivery Date")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        calendar = QCalendarWidget()
        calendar.setGridVisible(True)
        
        # Set current date if available
        if self.delivery_date:
            try:
                year, month, day = map(int, self.delivery_date.split('-'))
                calendar.setSelectedDate(QDate(year, month, day))
            except:
                pass
        
        layout.addWidget(calendar)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_date = calendar.selectedDate()
            date_str = selected_date.toString("yyyy-MM-dd")
            self.delivery_date_edit.setText(date_str)
    
    def update_project_name(self):
        """Update project name in database - fixed to prevent crash"""
        new_name = self.project_name_edit.text()
        if new_name != self.project_name:
            self.project_name = new_name
            conn = sqlite3.connect('file_tree_manager.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, self.project_id))
            conn.commit()
            conn.close()
            
            # Update tab text - fixed to get the correct parent
            tab_widget = self.parent().parent()  # Get the QTabWidget
            if hasattr(tab_widget, 'setTabText'):
                index = tab_widget.indexOf(self)
                if index >= 0:
                    tab_widget.setTabText(index, new_name)
    
    def update_project_comment(self):
        """Update project comment in database"""
        comment = self.project_comment_edit.toPlainText()
        self.project_comment = comment
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET project_comment = ? WHERE id = ?", (comment, self.project_id))
        conn.commit()
        conn.close()
    
    def update_delivery_date(self, date):
        """Update delivery date in database"""
        self.delivery_date = date
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET delivery_date = ? WHERE id = ?", (date, self.project_id))
        conn.commit()
        conn.close()
    
    def show_path(self, path):
        """Show path in details panel"""
        self.details_panel.setHtml(f"<h3>Path Information</h3><b>Path:</b> {path}")
        
    def save_tree_state(self):
        """Save the expanded state of the tree"""
        expanded_paths = []
        model = self.tree_view.model()
        
        def collect_expanded(index):
            if self.tree_view.isExpanded(index):
                path = model.filePath(index)
                expanded_paths.append(path)
                for i in range(model.rowCount(index)):
                    child_index = model.index(i, 0, index)
                    collect_expanded(child_index)
        
        collect_expanded(self.tree_view.rootIndex())
        self.settings.setValue(f"tree_expanded_{self.project_id}", expanded_paths)
        
    def restore_tree_state(self):
        """Restore the expanded state of the tree"""
        expanded_paths = self.settings.value(f"tree_expanded_{self.project_id}", [])
        if expanded_paths:
            model = self.tree_view.model()
            
            def expand_paths(index):
                path = model.filePath(index)
                if path in expanded_paths:
                    self.tree_view.expand(index)
                for i in range(model.rowCount(index)):
                    child_index = model.index(i, 0, index)
                    expand_paths(child_index)
            
            # Use a timer to ensure the tree is fully loaded before expanding
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: expand_paths(self.tree_view.rootIndex()))
    
    def closeEvent(self, event):
        """Save state when closing"""
        # Save splitter states
        main_splitter = self.findChild(QSplitter)
        if main_splitter:
            self.settings.setValue(f"main_splitter_{self.project_id}", main_splitter.saveState())
        
        details_splitter = self.findChild(QSplitter, "details_splitter")
        if details_splitter:
            self.settings.setValue(f"details_splitter_{self.project_id}", details_splitter.saveState())
                
        self.save_tree_state()
        super().closeEvent(event)
    
    def on_item_clicked(self, index):
        """Show details of the selected item"""
        path = self.file_model.filePath(index)
        if os.path.exists(path) and not path.endswith('.json'):
            # Get attributes
            publish_status, pub_time, pub_user = self.attribute_manager.get_current_status(path, "publish")
            client_status, client_time, client_user = self.attribute_manager.get_current_status(path, "to_client")
            
            # Format details text
            details = f"<h3>File Details</h3>"
            details += f"<b>Path:</b> {path}<br><br>"
            
            details += f"<b>Publish Status:</b> {'Published' if publish_status else 'Not Published'}<br>"
            if pub_time:
                details += f"<b>Publish Time:</b> {pub_time}<br>"
                details += f"<b>Published by:</b> {pub_user}<br>"
            details += "<br>"
            
            details += f"<b>Client Status:</b> {'Sent to Client' if client_status else 'Not Sent'}<br>"
            if client_time:
                details += f"<b>Client Time:</b> {client_time}<br>"
                details += f"<b>Sent by:</b> {client_user}<br>"
            
            # Add history if available
            data = self.attribute_manager.load_data(path)
            if data["publish"] or data["to_client"]:
                details += "<hr><h4>History</h4>"
                
                for history in data["publish"][-5:]:
                    status = "Published" if history["status"] else "Unpublished"
                    details += f"{status} by {history.get('user', 'Unknown')} at {history['timestamp']}<br>"
                
                for history in data["to_client"][-5:]:
                    status = "Sent to client" if history["status"] else "Removed from client"
                    details += f"{status} by {history.get('user', 'Unknown')} at {history['timestamp']}<br>"
            
            self.details_panel.setHtml(details)
    
    def check_attribute_conflicts(self, path, attribute):
        """Check for attribute conflicts in the same directory"""
        if not os.path.isdir(os.path.dirname(path)):
            return True  # No conflict if not in a directory with siblings
            
        parent_dir = os.path.dirname(path)
        siblings = [f for f in os.listdir(parent_dir) if f != os.path.basename(path)]
        
        conflicts = []
        for sibling in siblings:
            sibling_path = os.path.join(parent_dir, sibling)
            status, _, _ = self.attribute_manager.get_current_status(sibling_path, attribute)
            if status:
                # Get history to find the oldest
                history = self.attribute_manager.get_attribute_history(sibling_path, attribute)
                if history:
                    conflicts.append({
                        'path': sibling_path,
                        'name': sibling,
                        'timestamp': history[0]['timestamp'] if history else ''
                    })
        
        if conflicts:
            # Sort by timestamp (oldest first)
            conflicts.sort(key=lambda x: x['timestamp'])
            
            msg = f"The following items in the same directory already have the '{attribute}' attribute:\n\n"
            for conflict in conflicts:
                msg += f"- {conflict['name']}\n"
            
            msg += "\nDo you want to remove the attribute from the oldest item(s) before proceeding?"
            
            reply = QMessageBox.question(self, "Attribute Conflict", msg, 
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Remove attribute from oldest conflicts
                for conflict in conflicts:
                    self.attribute_manager.update_attribute(conflict['path'], attribute, False, self.username)
                return True
            else:
                return False
        return True
    
    def show_context_menu(self, position):
        """Show right-click context menu for attribute management"""
        menu = QMenu()
        index = self.tree_view.indexAt(position)
        
        if index.isValid():
            path = self.file_model.filePath(index)
            if path.endswith('.json'):
                return  # Skip .json files
                
            is_dir = os.path.isdir(path)
            
            publish_action = QAction("Publish", self)
            publish_action.triggered.connect(lambda: self.toggle_attribute("publish", True, path))
            menu.addAction(publish_action)
            
            unpublish_action = QAction("Unpublish", self)
            unpublish_action.triggered.connect(lambda: self.toggle_attribute("publish", False, path))
            menu.addAction(unpublish_action)
            
            menu.addSeparator()
            
            to_client_action = QAction("Mark for Client", self)
            to_client_action.triggered.connect(lambda: self.toggle_attribute("to_client", True, path))
            menu.addAction(to_client_action)
            
            remove_client_action = QAction("Remove from Client", self)
            remove_client_action.triggered.connect(lambda: self.toggle_attribute("to_client", False, path))
            menu.addAction(remove_client_action)
            
            # Add "Send to Client" option for directories
            if is_dir:
                menu.addSeparator()
                send_to_client_action = QAction("Send to Client", self)
                send_to_client_action.triggered.connect(lambda: self.send_to_client(path))
                menu.addAction(send_to_client_action)
                
                # Add "Export XML" option for directories
                export_xml_action = QAction("Export Published XML", self)
                export_xml_action.triggered.connect(lambda: self.export_published_xml(path))
                menu.addAction(export_xml_action)
            
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))
    
    def send_to_client(self, dir_path):
        """Send files to the delivery folder, including all child files of folders marked for client"""
        try:
            # Find all files in directories with to_client attribute
            to_client_files = []
            
            def collect_files_from_dir(current_dir):
                client_status, _, _ = self.attribute_manager.get_current_status(current_dir, "to_client")
                if client_status:
                    # Include all files in this directory and subdirectories
                    for root, dirs, files in os.walk(current_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if not file_path.endswith('.json'):  # Skip .json files
                                to_client_files.append(file_path)
                else:
                    # Only include files explicitly marked for client
                    for item in os.listdir(current_dir):
                        item_path = os.path.join(current_dir, item)
                        if os.path.isfile(item_path) and not item_path.endswith('.json'):
                            file_client_status, _, _ = self.attribute_manager.get_current_status(item_path, "to_client")
                            if file_client_status:
                                to_client_files.append(item_path)
                        elif os.path.isdir(item_path):
                            collect_files_from_dir(item_path)
            
            collect_files_from_dir(dir_path)
            
            if not to_client_files:
                QMessageBox.information(self, "No Files", "No files marked for client delivery in this directory.")
                return
            
            # Create the corresponding directory structure in delivery folder
            rel_path = os.path.relpath(dir_path, self.master_path)
            dest_dir = os.path.join(self.delivery_path, rel_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy files without timestamp
            copied_count = 0
            for file_path in to_client_files:
                file_rel_path = os.path.relpath(file_path, self.master_path)
                dest_path = os.path.join(self.delivery_path, file_rel_path)
                
                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Copy file without timestamp
                shutil.copy2(file_path, dest_path)
                copied_count += 1
            
            QMessageBox.information(self, "Success", f"Successfully copied {copied_count} files to client delivery folder.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send files to client: {str(e)}")
    
    def export_published_xml(self, dir_path):
        """Export XML file with published files information for NLE software"""
        try:
            # Find all published files in the directory (including children of published folders)
            published_files = []
            
            def collect_published_files(current_dir):
                # Check if current directory is published
                dir_publish_status, _, _ = self.attribute_manager.get_current_status(current_dir, "publish")
                
                for root, dirs, files in os.walk(current_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if file_path.endswith('.json'):
                            continue  # Skip .json files
                            
                        # If parent directory is published, include all files
                        if dir_publish_status:
                            published_files.append(file_path)
                        else:
                            # Check if individual file is published
                            file_publish_status, _, _ = self.attribute_manager.get_current_status(file_path, "publish")
                            if file_publish_status:
                                published_files.append(file_path)
            
            collect_published_files(dir_path)
            
            if not published_files:
                QMessageBox.information(self, "No Files", "No published files found in this directory.")
                return
            
            # Create XML structure
            root = ET.Element("FileSequence")
            root.set("version", "1.0")
            root.set("exportDate", datetime.now().isoformat())
            root.set("project", self.project_name)
            
            # Group files by sequence (files with similar names and numbers)
            sequences = {}
            for file_path in published_files:
                file_name = os.path.basename(file_path)
                dir_name = os.path.dirname(file_path)
                
                # Try to detect sequence patterns (e.g., file_001.jpg, file_002.jpg)
                base_name = file_name
                number = None
                
                # Look for numbers in the filename
                import re
                match = re.search(r'(\d+)\.\w+$', file_name)
                if match:
                    number = match.group(1)
                    base_name = file_name[:match.start()]
                
                if base_name not in sequences:
                    sequences[base_name] = {
                        'files': [],
                        'directory': dir_name
                    }
                
                sequences[base_name]['files'].append({
                    'path': file_path,
                    'name': file_name,
                    'number': number
                })
            
            # Add sequences to XML
            for base_name, sequence in sequences.items():
                seq_elem = ET.SubElement(root, "Sequence")
                seq_elem.set("name", base_name)
                seq_elem.set("directory", sequence['directory'])
                
                for file_info in sorted(sequence['files'], key=lambda x: x['number'] or x['name']):
                    file_elem = ET.SubElement(seq_elem, "File")
                    file_elem.set("name", file_info['name'])
                    if file_info['number']:
                        file_elem.set("frame", file_info['number'])
                    file_elem.set("path", file_info['path'])
                    file_elem.set("size", str(os.path.getsize(file_info['path'])))
                    file_elem.set("modified", datetime.fromtimestamp(os.path.getmtime(file_info['path'])).isoformat())
            
            # Create XML tree and save
            tree = ET.ElementTree(root)
            xml_file_path = os.path.join(dir_path, "published_sequence.xml")
            tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
            
            QMessageBox.information(self, "Success", f"XML export completed successfully.\nSaved to: {xml_file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export XML: {str(e)}")
    
    def toggle_attribute(self, attribute, value, path):
        """Toggle attribute for selected items with conflict checking"""
        if value:  # Only check conflicts when adding attributes
            if not self.check_attribute_conflicts(path, attribute):
                return  # User cancelled the operation
        
        self.attribute_manager.update_attribute(path, attribute, value, self.username)
        
        # Refresh the tree view to update badges
        self.tree_view.viewport().update()
        
        # Update details view
        index = self.tree_view.currentIndex()
        if index.isValid():
            self.on_item_clicked(index)


class CommandCenter(QMainWindow):
    """Main application window"""
    def __init__(self, user_id, username):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.settings = QSettings("FileTreeManager", "MainWindow")
        
        self.setWindowTitle(f"File Tree Manager - Command Center (User: {username})")
        self.setGeometry(100, 100, 1400, 900)
        
        # Setup UI
        self.setup_ui()
        
        # Load projects
        self.load_projects()
        
        # Restore window state
        self.restore_state()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Create menu bar
        self.setup_menu_bar()
        
        # Create corner widget for tab bar with buttons
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(5)
        
        new_project_btn = QPushButton("New Project")
        new_project_btn.clicked.connect(self.create_new_project)
        corner_layout.addWidget(new_project_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_projects)
        corner_layout.addWidget(refresh_btn)

        corner_layout.addStretch()
        
        # Tab widget for projects
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setCornerWidget(corner_widget, Qt.TopRightCorner)
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.statusBar().showMessage(f"Logged in as {self.username} | Ready")
    
    def setup_menu_bar(self):
        """Setup the menu bar with File menu first, Access second"""
        menubar = self.menuBar()
        
        # File menu (first)
        file_menu = menubar.addMenu('File')
        
        new_project_action = QAction('New Project', self)
        new_project_action.triggered.connect(self.create_new_project)
        file_menu.addAction(new_project_action)
        
        refresh_action = QAction('Refresh', self)
        refresh_action.triggered.connect(self.refresh_projects)
        file_menu.addAction(refresh_action)
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Access menu (only show for admin) - second
        if self.username == "admin":
            access_menu = menubar.addMenu('Access')
            
            account_action = QAction('Account Management', self)
            account_action.triggered.connect(self.show_user_manager)
            access_menu.addAction(account_action)
    
    def show_user_manager(self):
        """Show the user management dialog"""
        dialog = UserManagerDialog(self)
        dialog.exec_()
    
    def restore_state(self):
        """Restore window state from settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
    
    def closeEvent(self, event):
        """Save window state when closing"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # Save state of all project tabs
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, 'closeEvent'):
                tab.closeEvent(event)
        
        super().closeEvent(event)
    
    def load_projects(self):
        """Load projects from database"""
        conn = sqlite3.connect('file_tree_manager.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, master_path, client_name, delivery_path 
            FROM projects 
            WHERE created_by = ? OR created_by = 1
        """, (self.user_id,))
        
        projects = cursor.fetchall()
        conn.close()
        
        self.tab_widget.clear()
        
        for project_id, name, master_path, client_name, delivery_path in projects:
            # Create directories if they don't exist
            os.makedirs(master_path, exist_ok=True)
            os.makedirs(delivery_path, exist_ok=True)
            
            # Create project tab
            tab = ProjectTab(project_id, name, master_path, client_name, delivery_path, self.username)
            self.tab_widget.addTab(tab, name)
            
        if not projects:
            self.statusBar().showMessage("No projects found. Create a new project to get started.")
    
    def refresh_projects(self):
        """Refresh the project list"""
        self.load_projects()
        self.statusBar().showMessage("Projects refreshed")
    
    def create_new_project(self):
        """Create a new project"""
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            project_data = dialog.get_project_data()
            
            if not project_data["name"] or not project_data["master_path"]:
                QMessageBox.warning(self, "Error", "Please fill in required fields")
                return
                
            # Check if root_sample directory exists
            script_dir = os.path.dirname(os.path.abspath(__file__))
            root_sample_path = os.path.join(script_dir, "folder_hierarchy", "root_sample")
            
            if not os.path.exists(root_sample_path):
                QMessageBox.warning(self, "Error", "Root sample directory not found. Please create it first.")
                return
                
            # Ask user if they want to create folder hierarchy
            reply = QMessageBox.question(self, "Create Folder Hierarchy", 
                                      "Do you want to create the folder hierarchy in the master directory?",
                                      QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    # Create project directory
                    project_dir = os.path.join(project_data["master_path"], project_data["name"])
                    os.makedirs(project_dir, exist_ok=True)
                    
                    # Copy root_sample contents to project directory
                    for item in os.listdir(root_sample_path):
                        source = os.path.join(root_sample_path, item)
                        destination = os.path.join(project_dir, item)
                        
                        if os.path.isdir(source):
                            shutil.copytree(source, destination, dirs_exist_ok=True)
                        else:
                            shutil.copy2(source, destination)
                    
                    # Update master path to the new project directory
                    project_data["master_path"] = project_dir
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create folder hierarchy: {str(e)}")
                    return
            
            # Set delivery path to a subdirectory of master path
            delivery_path = os.path.join(project_data["master_path"], "Deliveries")
            os.makedirs(delivery_path, exist_ok=True)
            
            # Save to database
            conn = sqlite3.connect('file_tree_manager.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (name, master_path, client_name, delivery_path, project_comment, delivery_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_data["name"], project_data["master_path"], project_data["client_name"], 
                 delivery_path, project_data["comment"], project_data["delivery_date"], self.user_id)
            )
            conn.commit()
            conn.close()
            
            # Refresh projects
            self.load_projects()
            self.statusBar().showMessage(f"Project '{project_data['name']}' created successfully")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Show login window
    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        # Login successful, show main window
        window = CommandCenter(login.user_id, login.username_str)
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)