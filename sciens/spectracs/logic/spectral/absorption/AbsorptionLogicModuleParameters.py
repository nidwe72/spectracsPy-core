class AbsorptionLogicModuleParameters:
    # Two-input op: absorbance A = -log10(sample / reference) (Beer-Lambert). referenceFloorFraction
    # guards the underlying division (None -> module default).

    reference = None
    sample = None
    referenceFloorFraction = None

    def setReference(self, reference):
        self.reference = reference

    def getReference(self):
        return self.reference

    def setSample(self, sample):
        self.sample = sample

    def getSample(self):
        return self.sample

    def setReferenceFloorFraction(self, referenceFloorFraction):
        self.referenceFloorFraction = referenceFloorFraction

    def getReferenceFloorFraction(self):
        return self.referenceFloorFraction
