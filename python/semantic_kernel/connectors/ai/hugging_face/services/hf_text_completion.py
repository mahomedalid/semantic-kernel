# Copyright (c) Microsoft. All rights reserved.

from logging import Logger
from typing import Optional


from semantic_kernel.connectors.ai.ai_exception import AIException
from semantic_kernel.connectors.ai.complete_request_settings import (
    CompleteRequestSettings,
)
from semantic_kernel.connectors.ai.text_completion_client_base import (
    TextCompletionClientBase,
)
from semantic_kernel.utils.null_logger import NullLogger


class HuggingFaceTextCompletion(TextCompletionClientBase):
    _model_id: str
    _task: str
    _device: int
    _log: Logger

    def __init__(
        self,
        model_id: str,
        device: Optional[int] = -1,
        task: Optional[str] = None,
        log: Optional[Logger] = None,
    ) -> None:
        """
        Initializes a new instance of the HuggingFaceTextCompletion class.

        Arguments:
            model_id {str} -- Hugging Face model card string, see
                https://huggingface.co/models
            device {Optional[int]} -- Device to run the model on, -1 for CPU, 0+ for GPU.
            task {Optional[str]} -- Model completion task type, options are:
                - summarization: takes a long text and returns a shorter summary.
                - text-generation: takes incomplete text and returns a set of completion candidates.
                - text2text-generation (default): takes an input prompt and returns a completion.
                text2text-generation is the default as it behaves more like GPT-3+.
            log {Optional[Logger]} -- Logger instance.

        Note that this model will be downloaded from the Hugging Face model hub.
        """
        self._model_id = model_id
        self._task = "text2text-generation" if task is None else task
        self._log = log if log is not None else NullLogger()

        try:
            import transformers
            import torch
        except (ImportError, ModuleNotFoundError):
            raise ImportError("Please ensure that torch and transformers are installed to use HuggingFaceTextCompletion")
        
        self.device = (
            "cuda:" + device if device >= 0 and torch.cuda.is_available() else "cpu"
        )
        self.generator = transformers.pipeline(
            task=self._task, model=self._model_id, device=self.device
        )

    async def complete_async(
        self, prompt: str, request_settings: CompleteRequestSettings
    ) -> str:
        """
        Completes a prompt using the Hugging Face model.

        Arguments:
            prompt {str} -- Prompt to complete.
            request_settings {CompleteRequestSettings} -- Request settings.

        Returns:
            str -- Completion result.
        """
        try:
            import transformers
            generation_config = transformers.GenerationConfig(
                temperature=request_settings.temperature,
                top_p=request_settings.top_p,
                max_new_tokens=request_settings.max_tokens,
                pad_token_id=50256,  # EOS token
            )
            result = self.generator(
                prompt, num_return_sequences=1, generation_config=generation_config
            )

            if self._task == "text-generation" or self._task == "text2text-generation":
                return result[0]["generated_text"]

            elif self._task == "summarization":
                return result[0]["summary_text"]

            else:
                raise AIException(
                    AIException.ErrorCodes.InvalidConfiguration,
                    "Unsupported hugging face pipeline task: only \
                        text-generation, text2text-generation, and summarization are supported.",
                )

        except Exception as e:
            raise AIException("Hugging Face completion failed", e)
