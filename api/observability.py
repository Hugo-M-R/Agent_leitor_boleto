"""
Módulo de Observabilidade com Langfuse
Centraliza configuração e helpers para rastreamento de traces/spans
"""

import os
import re
import uuid
from typing import Optional, Dict, Any, Callable
from functools import wraps
from pathlib import Path

# Configuração do Langfuse (opcional, controlado por env)
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower().strip('"').strip("'") in ("1", "true", "yes")

langfuse = None
_has_trace_method = False
_has_flush_method = False
if LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse
        langfuse = Langfuse()
        import logging
        logger = logging.getLogger(__name__)
        logger.info("✅ Langfuse inicializado com sucesso!")
        logger.info(f"   Host: {os.getenv('LANGFUSE_HOST', 'não configurado')}")
        logger.info(f"   Public Key: {os.getenv('LANGFUSE_PUBLIC_KEY', 'não configurado')[:20]}...")
        # Detecta métodos disponíveis
        _has_trace_method = hasattr(langfuse, "trace")
        _has_flush_method = hasattr(langfuse, "flush")
        logger.info(f"   Método .trace() disponível: {_has_trace_method}")
        logger.info(f"   Método .flush() disponível: {_has_flush_method}")
        
        # Lista métodos disponíveis para debug
        methods = [m for m in dir(langfuse) if not m.startswith('_') and callable(getattr(langfuse, m, None))]
        logger.info(f"   Métodos disponíveis: {', '.join(methods[:10])}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Langfuse não pôde ser inicializado: {e}")
        logger.error(f"   Verifique LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY e LANGFUSE_HOST")
        import traceback
        traceback.print_exc()
        langfuse = None
else:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("ℹ️  Langfuse desabilitado (LANGFUSE_ENABLED não está 'true')")


def mask_pii(value: Optional[str]) -> Optional[str]:
    """
    Mascara dados sensíveis (CNPJ, CPF, linha digitável) para privacidade.
    
    Args:
        value: String que pode conter PII
        
    Returns:
        String mascarada ou None
    """
    if not value or not isinstance(value, str):
        return value
    
    # Remove formatação para análise
    digits = re.sub(r"[^\d]", "", value)
    
    # CNPJ (14 dígitos)
    if len(digits) == 14:
        return f"XX.XXX.XXX/XXXX-{digits[-2:]}"
    
    # CPF (11 dígitos)
    if len(digits) == 11:
        return f"XXX.XXX.XXX-{digits[-2:]}"
    
    # Linha digitável (47 dígitos ou similar)
    if len(digits) >= 20:
        return f"{digits[:6]}…{digits[-6:]}"
    
    # Outros valores longos: truncar
    if len(value) > 8:
        return value[:4] + "…"
    
    return value


class _TraceAdapter:
    """Adapter para compatibilizar API v1 com interface update()/end()."""
    def __init__(self, client, trace_id: str):
        self.client = client
        self.trace_id = trace_id

    def update(self, output: Optional[Dict[str, Any]] = None):
        try:
            if output:
                # v1: update_trace(id=..., output=...)
                update = getattr(self.client, "update_trace", None)
                if callable(update):
                    update(id=self.trace_id, output=output)
        except Exception:
            pass

    def end(self):
        # Nada específico para encerrar no v1
        pass


class _SpanAdapter:
    def __init__(self, client, observation_id: str):
        self.client = client
        self.observation_id = observation_id

    def update(self, output: Optional[Dict[str, Any]] = None):
        try:
            if output:
                update_obs = getattr(self.client, "update_observation", None)
                if callable(update_obs):
                    update_obs(id=self.observation_id, output=output)
        except Exception:
            pass

    def end(self):
        # Nada específico para encerrar no v1
        pass


class TraceContext:
    """Context manager para traces usando API v3 do Langfuse (suporta async)"""
    def __init__(self, client, name: str, input_data: Optional[Dict[str, Any]] = None, **kwargs):
        self.client = client
        self.name = name
        self.input_data = input_data
        self.kwargs = kwargs
        self.span_context = None
    
    def __enter__(self):
        if not self.client:
            return self
        
        # Mascara PII no input
        safe_input = {}
        if self.input_data:
            for k, v in self.input_data.items():
                if isinstance(v, str):
                    safe_input[k] = mask_pii(v)
                else:
                    safe_input[k] = v
        
        # Usa start_as_current_span como context manager (API v3)
        try:
            # API v3: start_as_current_span aceita (name, input).
            # Campos adicionais serão enviados via update_current_trace abaixo.
            self.span_context = self.client.start_as_current_span(
                name=self.name,
                input=safe_input,
            )
            if self.span_context:
                self.span_context.__enter__()
            
            # Atualiza trace com input
            try:
                payload = {"input": safe_input}
                if self.kwargs:
                    # envia metadados adicionais em um campo metadata
                    payload["metadata"] = self.kwargs
                self.client.update_current_trace(**payload)
            except Exception:
                pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao criar trace context: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span_context:
            try:
                self.span_context.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass
        
        # Flush para garantir envio
        if _has_flush_method:
            try:
                self.client.flush()
            except Exception:
                pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.__exit__(exc_type, exc_val, exc_tb)
    
    def update(self, output: Optional[Dict[str, Any]] = None):
        """Atualiza o trace atual"""
        if not self.client:
            return
        try:
            if output:
                self.client.update_current_trace(output=output)
        except Exception:
            pass


def create_trace(name: str, input_data: Optional[Dict[str, Any]] = None, **kwargs):
    """
    Cria um trace no Langfuse (API v3).
    Retorna um context manager que deve ser usado com 'with'.
    
    Args:
        name: Nome do trace
        input_data: Dados de entrada (serão mascarados automaticamente)
        **kwargs: Argumentos adicionais
        
    Returns:
        TraceContext (context manager) ou None se Langfuse desabilitado
        
    Exemplo:
        with create_trace("meu-trace", input_data={"teste": "valor"}):
            # código aqui
            pass
    """
    if not langfuse:
        return None
    
    return TraceContext(langfuse, name, input_data, **kwargs)


class SpanContext:
    """Context manager para spans usando API v3 do Langfuse (suporta async)"""
    def __init__(self, client, name: str, input_data: Optional[Dict[str, Any]] = None, **kwargs):
        self.client = client
        self.name = name
        self.input_data = input_data
        self.kwargs = kwargs
        self.span_context = None
    
    def __enter__(self):
        if not self.client:
            return self
        
        # Mascara PII no input
        safe_input = {}
        if self.input_data:
            for k, v in self.input_data.items():
                if isinstance(v, str):
                    safe_input[k] = mask_pii(v)
                else:
                    safe_input[k] = v
        
        # Usa start_as_current_span (API v3)
        try:
            self.span_context = self.client.start_as_current_span(
                name=self.name,
                input=safe_input,
                **self.kwargs
            )
            if self.span_context:
                self.span_context.__enter__()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao criar span context: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span_context:
            try:
                self.span_context.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.__exit__(exc_type, exc_val, exc_tb)
    
    def update(self, output: Optional[Dict[str, Any]] = None):
        """Atualiza o span atual"""
        if not self.client:
            return
        try:
            if output:
                self.client.update_current_span(output=output)
        except Exception:
            pass
    
    def end(self):
        """Finaliza o span (compatibilidade com API antiga)"""
        # Já finalizado pelo context manager
        pass


def create_span(name: str, input_data: Optional[Dict[str, Any]] = None, **kwargs):
    """
    Cria um span no Langfuse (API v3).
    Retorna um context manager que deve ser usado com 'with'.
    
    Args:
        name: Nome do span
        input_data: Dados de entrada (serão mascarados automaticamente)
        **kwargs: Argumentos adicionais
        
    Returns:
        SpanContext (context manager) ou None se Langfuse desabilitado
        
    Exemplo:
        with create_span("meu-span", input_data={"teste": "valor"}):
            # código aqui
            pass
    """
    if not langfuse:
        return None
    
    return SpanContext(langfuse, name, input_data, **kwargs)


def log_error(message: str, level: str = "ERROR"):
    """
    Registra um erro/log no Langfuse.
    
    Args:
        message: Mensagem de erro
        level: Nível do log (ERROR, WARNING, INFO)
    """
    if not langfuse:
        return
    
    try:
        from langfuse.model import Level as LangfuseLevel
        level_map = {
            "ERROR": LangfuseLevel.ERROR,
            "WARNING": LangfuseLevel.WARNING,
            "INFO": LangfuseLevel.INFO,
        }
        langfuse.log(name="error", message=message, level=level_map.get(level, LangfuseLevel.ERROR))
    except Exception:
        pass  # Falha silenciosa se Langfuse não disponível


def trace_function(name: Optional[str] = None):
    """
    Decorator para rastrear automaticamente funções.
    
    Args:
        name: Nome do trace (padrão: nome da função)
        
    Exemplo:
        @trace_function(name="ocr_processing")
        def ocr_pdf(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            trace_name = name or func.__name__
            trace = create_trace(name=trace_name, input_data={"function": func.__name__})
            
            try:
                result = func(*args, **kwargs)
                if trace:
                    trace.update(output={"success": True})
                return result
            except Exception as e:
                if trace:
                    trace.update(output={"error": str(e)})
                    log_error(f"{func.__name__}: {e}")
                raise
            finally:
                if trace:
                    trace.end()
        
        return wrapper
    return decorator


def get_langfuse_client():
    """
    Retorna o cliente Langfuse se disponível.
    
    Returns:
        Langfuse client ou None
    """
    return langfuse


def is_enabled() -> bool:
    """
    Verifica se Langfuse está habilitado e funcionando.
    
    Returns:
        True se Langfuse está ativo
    """
    return langfuse is not None

