class SpectralPlugin:
    # One class, five per-phase hooks (concept §9.4). Qt-free; imports only plugin_sdk. Each hook mutates
    # the passed SpectralWorkflow: interactive phases DECLARE steps, computed phases CREATE+FILL them; a
    # hook that creates zero steps makes the host auto-skip that phase. (SPEC_pumpkin_integration.md B.4)

    title = None

    def acquisition(self, workflow):
        raise NotImplementedError

    def processing(self, workflow):
        raise NotImplementedError

    def evaluation(self, workflow):
        raise NotImplementedError

    def metadata(self, workflow):
        # Return a list[MetadataField] describing the editable metadata form (empty = no metadata).
        # This hook DESCRIBES fields (it does not mutate the workflow like the others).
        return []

    def publishing(self, workflow):
        pass  # empty -> phase skipped
