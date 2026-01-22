"""
Sistema de dump de iteraciones del optimizador.

Captura snapshots de cada iteración del proceso de optimización,
mostrando cómo evolucionan las posiciones de todos los elementos.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict


class IterationDumper:
    """Captura y serializa el estado del layout en cada iteración del optimizador."""

    def __init__(self, input_file: str, output_dir: str = "debug/iterations"):
        """
        Inicializa el dumper.

        Args:
            input_file: Ruta del archivo .gag de entrada
            output_dir: Directorio donde guardar los dumps (relativo a cwd)
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp único para este dump
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Nombre base del archivo (sin ruta ni extensión)
        self.base_name = Path(input_file).stem

        # Datos capturados
        self.metadata: Dict[str, Any] = {
            "gag_version": "3.0.0",
            "input_file": input_file,
            "timestamp": datetime.now().isoformat(),
            "initial_collisions": 0,
            "final_collisions": 0,
            "canvas_initial": {"width": 0, "height": 0},
            "canvas_final": {"width": 0, "height": 0}
        }

        self.iterations: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def capture_initial_state(self, layout, initial_collisions: int) -> None:
        """
        Captura el estado inicial antes de comenzar optimización.

        Args:
            layout: Layout inicial
            initial_collisions: Número de colisiones iniciales
        """
        self.metadata["initial_collisions"] = initial_collisions
        self.metadata["canvas_initial"] = {
            "width": layout.canvas['width'],
            "height": layout.canvas['height']
        }

        # Capturar iteración 0 (estado inicial)
        initial_iteration = {
            "iteration": 0,
            "type": "initial",
            "timestamp": datetime.now().isoformat(),
            "state": self._serialize_layout(layout),
            "collisions": self._serialize_collisions(layout, initial_collisions),
            "metrics": {
                "collision_count": initial_collisions,
                "canvas_width": layout.canvas['width'],
                "canvas_height": layout.canvas['height'],
                "total_elements": len(layout.elements),
                "total_connections": len(layout.connections)
            }
        }

        self.iterations.append(initial_iteration)

    def capture_iteration(
        self,
        iteration_num: int,
        layout_before,
        layout_after,
        strategy_type: str,
        strategy_desc: str,
        changes: List[Dict[str, Any]],
        collisions_before: int,
        collisions_after: int,
        accepted: bool,
        became_best: bool
    ) -> None:
        """
        Captura una iteración del optimizador.

        Args:
            iteration_num: Número de iteración (1-10)
            layout_before: Layout antes de aplicar estrategia
            layout_after: Layout después de aplicar estrategia
            strategy_type: Tipo de estrategia aplicada
            strategy_desc: Descripción de la estrategia
            changes: Lista de cambios aplicados
            collisions_before: Colisiones antes de la estrategia
            collisions_after: Colisiones después de la estrategia
            accepted: Si la iteración fue aceptada
            became_best: Si se convirtió en el mejor layout
        """
        iteration_data = {
            "iteration": iteration_num,
            "type": "optimization",
            "timestamp": datetime.now().isoformat(),
            "state_before": self._serialize_layout(layout_before),
            "strategy_applied": {
                "type": strategy_type,
                "description": strategy_desc,
                "changes": changes
            },
            "state_after": self._serialize_layout(layout_after),
            "collisions_before": self._serialize_collisions(layout_before, collisions_before),
            "collisions_after": self._serialize_collisions(layout_after, collisions_after),
            "metrics": {
                "collision_improvement": collisions_before - collisions_after,
                "collision_count_before": collisions_before,
                "collision_count_after": collisions_after,
                "accepted": accepted,
                "became_best": became_best,
                "canvas_expanded": layout_after.canvas['width'] > layout_before.canvas['width'] or
                                  layout_after.canvas['height'] > layout_before.canvas['height'],
                "elements_moved": len([c for c in changes if c.get("type") == "element_moved"]),
                "labels_relocated": len([c for c in changes if c.get("type") == "label_relocated"])
            }
        }

        self.iterations.append(iteration_data)

    def save(self, final_layout, final_collisions: int) -> str:
        """
        Guarda el dump completo a JSON.

        Args:
            final_layout: Layout final después de optimización
            final_collisions: Número final de colisiones

        Returns:
            Ruta del archivo JSON generado
        """
        self.metadata["final_collisions"] = final_collisions
        self.metadata["canvas_final"] = {
            "width": final_layout.canvas['width'],
            "height": final_layout.canvas['height']
        }

        # Generar resumen
        summary = self._generate_summary()

        # Construir JSON completo
        dump_data = {
            "metadata": self.metadata,
            "iterations": self.iterations,
            "summary": summary
        }

        # Guardar a archivo
        output_file = self.output_dir / f"{self.base_name}_iterations_{self.timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, indent=2, ensure_ascii=False)

        return str(output_file)

    def _serialize_layout(self, layout) -> Dict[str, Any]:
        """Serializa el estado completo del layout."""
        return {
            "elements": self._serialize_elements(layout.elements),
            "connections": self._serialize_connections(layout.connections),
            "canvas": {
                "width": layout.canvas['width'],
                "height": layout.canvas['height']
            }
        }

    def _serialize_elements(self, elements: List[Dict]) -> List[Dict[str, Any]]:
        """Serializa lista de elementos con todas sus propiedades."""
        serialized = []

        for elem in elements:
            elem_data = {
                "id": elem.get("id"),
                "type": elem.get("type"),
                "x": round(elem.get("x", 0), 2),
                "y": round(elem.get("y", 0), 2),
                "width": round(elem.get("width", 0), 2) if elem.get("width") else None,
                "height": round(elem.get("height", 0), 2) if elem.get("height") else None,
                "label": elem.get("label"),
                "priority": elem.get("priority"),
                "level": elem.get("level"),
                "group": elem.get("group")
            }

            # Incluir coordenadas de etiqueta si existen
            if "label_x" in elem and "label_y" in elem:
                elem_data["label_coords"] = {
                    "x": round(elem["label_x"], 2),
                    "y": round(elem["label_y"], 2)
                }

            # Incluir elementos contenidos si es un contenedor
            if "elements" in elem and elem["elements"]:
                elem_data["contained_elements"] = [e.get("id") for e in elem["elements"]]

            serialized.append(elem_data)

        return serialized

    def _serialize_connections(self, connections: List[Dict]) -> List[Dict[str, Any]]:
        """Serializa lista de conexiones."""
        serialized = []

        for conn in connections:
            conn_data = {
                "from": conn.get("from"),
                "to": conn.get("to"),
                "label": conn.get("label")
            }

            # Incluir waypoints si existen
            if "waypoints" in conn and conn["waypoints"]:
                conn_data["waypoints"] = [
                    {"x": round(wp["x"], 2), "y": round(wp["y"], 2)}
                    for wp in conn["waypoints"]
                ]

            # Incluir coordenadas de etiqueta si existen
            if "label_x" in conn and "label_y" in conn:
                conn_data["label_coords"] = {
                    "x": round(conn["label_x"], 2),
                    "y": round(conn["label_y"], 2)
                }

            serialized.append(conn_data)

        return serialized

    def _serialize_collisions(self, layout, collision_count: int) -> Dict[str, Any]:
        """Serializa información de colisiones."""
        # Por ahora solo retornamos el count
        # En el futuro podríamos incluir pairs de elementos que colisionan
        return {
            "count": collision_count
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Genera resumen estadístico del proceso de optimización."""
        duration_ms = int((datetime.now() - self.start_time).total_seconds() * 1000)

        # Contar iteraciones exitosas (que mejoraron)
        successful_improvements = sum(
            1 for it in self.iterations[1:]  # Saltar initial
            if it["metrics"].get("became_best", False)
        )

        # Calcular reducción de colisiones
        initial = self.metadata["initial_collisions"]
        final = self.metadata["final_collisions"]
        reduction = initial - final
        percent = (reduction / initial * 100) if initial > 0 else 0

        # Timeline de mejoras
        timeline = []
        for it in self.iterations:
            if it["type"] == "initial":
                timeline.append({
                    "iteration": 0,
                    "collisions": initial,
                    "improvement": 0,
                    "event": "Estado inicial"
                })
            elif it["metrics"].get("became_best", False):
                timeline.append({
                    "iteration": it["iteration"],
                    "collisions": it["metrics"]["collision_count_after"],
                    "improvement": it["metrics"]["collision_improvement"],
                    "event": f"Mejora con {it['strategy_applied']['type']}"
                })

        # Canvas expansion
        canvas_expanded = (
            self.metadata["canvas_final"]["width"] > self.metadata["canvas_initial"]["width"] or
            self.metadata["canvas_final"]["height"] > self.metadata["canvas_initial"]["height"]
        )

        summary = {
            "total_iterations": len(self.iterations) - 1,  # Sin contar initial
            "successful_improvements": successful_improvements,
            "collision_reduction": {
                "initial": initial,
                "final": final,
                "reduction": reduction,
                "percent_improvement": round(percent, 1)
            },
            "canvas_expansion": {
                "occurred": canvas_expanded,
                "initial": self.metadata["canvas_initial"],
                "final": self.metadata["canvas_final"]
            },
            "duration_ms": duration_ms,
            "timeline": timeline
        }

        return summary
