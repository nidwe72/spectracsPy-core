class TransmissionLogicModuleParameters:
    # Two-input op: transmittance T = sample / reference. referenceFloorFraction guards the division
    # where the reference is ~0 (a dip/edge) by masking those wavelengths (None -> module default).

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
