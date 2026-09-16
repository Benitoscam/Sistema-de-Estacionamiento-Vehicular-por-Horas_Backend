"""Excepciones del dominio — Fase 2A (un solo módulo, códigos HTTP incluidos)."""


class ErrorDominio(Exception):
    estado_http = 400

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


class RangoInvalido(ErrorDominio):
    estado_http = 400


class EspacioNoDisponible(ErrorDominio):
    estado_http = 409


class ReservaNoCancelabe(ErrorDominio):
    estado_http = 409


class PagoDuplicado(ErrorDominio):
    estado_http = 409


class PermisoDenegado(ErrorDominio):
    estado_http = 403


class RecursoNoEncontrado(ErrorDominio):
    estado_http = 404
