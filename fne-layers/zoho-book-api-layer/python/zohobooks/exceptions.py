class EmptyProductListError(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message
    
class ZCRMPotentialIDMissing(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message
    
class CustomerIDNotFound(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message
    
class EstimateIDNotFound(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message
    
class ZCRMInvalidID(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message