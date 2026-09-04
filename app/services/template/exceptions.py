class TemplateAnalysisError(Exception):
    """Base class for expected template-analysis failures."""

class TemplateAnalysisConfigurationError(TemplateAnalysisError):
    pass

class TemplateFileTooLargeError(TemplateAnalysisError):
    pass

class UnsupportedTemplateFileError(TemplateAnalysisError):
    pass

class EmptyTemplateFileError(TemplateAnalysisError):
    pass

class UnprocessableTemplateFileError(TemplateAnalysisError):
    pass

class LLMUnavailableError(TemplateAnalysisError):
    pass

class LLMTimeoutError(TemplateAnalysisError):
    pass

class LLMUpstreamError(TemplateAnalysisError):
    pass

class InvalidLLMResponseError(TemplateAnalysisError):
    pass
