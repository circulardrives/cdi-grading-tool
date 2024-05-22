"""
Circular Drive Initiative - Main

@language    Python 3.12
@framework   PySide 6
@version     2.0.0
"""

# Modules
import sys

# Circular Drive Initiative
from CDI import CDIGradingTool

# PySide6
from PySide6.QtWidgets import QApplication

# Exceptions
from classes.exceptions import CDIException, ConfigurationException, SystemException

# Main Function
if __name__ == '__main__':

    # Try
    try:
        # Set Qt Application
        app = QApplication(sys.argv)

        # Load CDI Grading Tool
        cdi_grading_tool = CDIGradingTool()

        # Setup CDI Grading Tool
        cdi_grading_tool.do_initial_setup()

        # Execute Qt Application
        sys.exit(app.exec())

    # Catch
    except CDIException as exception:
        # Exit
        sys.exit(exception.message)
    # Catch
    except ConfigurationException as exception:
        # Exit
        sys.exit(exception.message)
    # Catch
    except SystemException as exception:
        # Exit
        sys.exit(exception.message)
