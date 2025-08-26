import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QMessageBox, QTextEdit)

class FolderCreatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.root_path = ""
        self.root_name = ""
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Folder Structure Creator')
        self.setGeometry(100, 100, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Root directory selection
        dir_layout = QHBoxLayout()
        dir_label = QLabel('Root Directory:')
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)
        
        # Root name input
        name_layout = QHBoxLayout()
        name_label = QLabel('Root Folder Name:')
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Create button
        self.create_btn = QPushButton('Create Folder Structure')
        self.create_btn.clicked.connect(self.confirm_creation)
        layout.addWidget(self.create_btn)
        
        # Status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        layout.addWidget(self.status_display)
        
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, 'Select Root Directory')
        if directory:
            self.root_path = directory
            self.dir_input.setText(directory)
            
    def confirm_creation(self):
        self.root_name = self.name_input.text().strip()
        
        if not self.root_path:
            QMessageBox.warning(self, 'Warning', 'Please select a root directory.')
            return
            
        if not self.root_name:
            QMessageBox.warning(self, 'Warning', 'Please enter a root folder name.')
            return
            
        full_path = os.path.join(self.root_path, self.root_name)
        
        if os.path.exists(full_path):
            QMessageBox.warning(self, 'Warning', f'A folder named "{self.root_name}" already exists in the selected directory.')
            return
            
        # First confirmation
        reply = QMessageBox.question(self, 'Confirmation', 
                                   f'The root folder will be created at:\n{full_path}\n\nDo you want to proceed?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Second confirmation
            reply2 = QMessageBox.question(self, 'Final Confirmation', 
                                       'Are you sure you want to create the folder structure?',
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply2 == QMessageBox.Yes:
                self.create_folder_structure(full_path)
                
    def create_folder_structure(self, root_path):
        try:
            os.makedirs(root_path)
            self.status_display.append(f"Created root folder: {root_path}")
            
            # Define the folder structure based on the document
            folder_structure = [
                "01_Project_Data/01_StoryBoard_and_Script",
                "01_Project_Data/02_References",
                "01_Project_Data/03_Work_Material/01_Images",
                "01_Project_Data/03_Work_Material/02_Footage",
                "01_Project_Data/03_Work_Material/03_Audio",
                "01_Project_Data/03_Work_Material/04_Models",
                "01_Project_Data/04_Calendar",
                "01_Project_Data/05_Cam_Info",
                "01_Project_Data/06_Feedback",
                
                "02_2D_Projects/01_PSD",
                "02_2D_Projects/02_Illustrator",
                
                "3D_Project/01_Softwares/01_Max/01_Pre-Prod/01_RND",
                "3D_Project/01_Softwares/01_Max/01_Pre-Prod/02_Models",
                "3D_Project/01_Softwares/01_Max/01_Pre-Prod/03_Rigging",
                "3D_Project/01_Softwares/01_Max/01_Pre-Prod/04_Lookdev",
                "3D_Project/01_Softwares/01_Max/01_Pre-Prod/05_Render",
                "3D_Project/01_Softwares/01_Max/02_Prod/01_Scenes/Shot_Structure/Anim",
                "3D_Project/01_Softwares/01_Max/02_Prod/01_Scenes/Shot_Structure/Render_Scenes",
                "3D_Project/01_Softwares/01_Max/02_Prod/02_Render/Shot_Structure",
                "3D_Project/01_Softwares/01_Max/03_Sims",
                "3D_Project/01_Softwares/01_Max/04_Matlibs",
                
                "3D_Project/01_Softwares/02_Maya/01_Pre-Prod/01_RND",
                "3D_Project/01_Softwares/02_Maya/01_Pre-Prod/02_Models",
                "3D_Project/01_Softwares/02_Maya/01_Pre-Prod/03_Rigging",
                "3D_Project/01_Softwares/02_Maya/01_Pre-Prod/04_Lookdev",
                "3D_Project/01_Softwares/02_Maya/01_Pre-Prod/05_Render",
                "3D_Project/01_Softwares/02_Maya/02_Prod/01_Scenes/Shot_Structure/Anim",
                "3D_Project/01_Softwares/02_Maya/02_Prod/01_Scenes/Shot_Structure/Render_Scenes",
                "3D_Project/01_Softwares/02_Maya/02_Prod/02_Renders/Shot_Structure",
                
                "3D_Project/01_Softwares/03_Houdini/01_Pre-prod/01_Scenes",
                "3D_Project/01_Softwares/03_Houdini/01_Pre-prod/02_Collect",
                "3D_Project/01_Softwares/03_Houdini/01_Pre-prod/03_Renders",
                "3D_Project/01_Softwares/03_Houdini/02_Prod/01_Scenes",
                "3D_Project/01_Softwares/03_Houdini/02_Prod/02_Collect",
                "3D_Project/01_Softwares/03_Houdini/02_Prod/03_Renders",
                
                "3D_Project/01_Softwares/04_Unreal/01_Scenes/Shot_Structure",
                "3D_Project/01_Softwares/04_Unreal/02_Render/Shot_Structure",
                
                "3D_Project/01_Softwares/05_ZBrush/01_Scenes",
                "3D_Project/01_Softwares/05_ZBrush/02_Work_Images",
                
                "3D_Project/01_Softwares/06_Substance/01_Scenes",
                "3D_Project/01_Softwares/06_Substance/02_Work_Images",
                
                "3D_Project/02_Export/01_Assets",
                "3D_Project/02_Export/02_Shots/Shot_Structure",
                
                "3D_Project/03_Capture/01_Pre-prod",
                "3D_Project/03_Capture/02_Prod/Shot_Structure",
                
                "3D_Project/04_Textures",
                
                "04_Tracking/01_PFTrack",
                "04_Tracking/02_AE",
                "04_Tracking/03_C4D",
                "04_Tracking/004_SynthEyes",
                "04_Tracking/005_PFTrack",
                
                "05_Compositing/01_Comp_Scenes/01_Slate",
                "05_Compositing/02_PreComp_Renders",
                "05_Compositing/03_Comp_Renders",
                "05_Compositing/04_Edit/Output",
                "05_Compositing/04_Edit/Work",
                
                "06_Internal_Review",
                "07_Out_To_Client"
            ]
            
            # Create all folders
            for folder in folder_structure:
                folder_path = os.path.join(root_path, folder)
                os.makedirs(folder_path, exist_ok=True)
                self.status_display.append(f"Created: {folder_path}")
                
            self.status_display.append("\nFolder structure created successfully!")
            QMessageBox.information(self, 'Success', 'Folder structure created successfully!')
            
        except Exception as e:
            self.status_display.append(f"Error: {str(e)}")
            QMessageBox.critical(self, 'Error', f'An error occurred: {str(e)}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FolderCreatorApp()
    window.show()
    sys.exit(app.exec_())