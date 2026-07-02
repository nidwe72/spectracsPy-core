class MetadataField:
    # A plugin-declared metadata field spec (Qt-free), returned by SpectralPlugin.metadata(). The wizard
    # builds the editable METADATA form from these; on Save they become self-describing
    # SpectralWorkflowMetadata rows. type ∈ {TEXT, NUMBER, DATE}; showInWorkflowsTable → a Home-list column.
    # (SPEC_workflow_persistence.md §2.3)

    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"

    def __init__(self, name, label, type=TEXT, showInWorkflowsTable=False, order=0):
        self.name = name
        self.label = label
        self.type = type
        self.showInWorkflowsTable = showInWorkflowsTable
        self.order = order
