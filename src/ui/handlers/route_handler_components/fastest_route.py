"""Fastest-route and auto-fix flows extracted from `RouteHandler`."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger(__name__)


def find_fastest_route(*, handler) -> None:
    """Find the fastest route between from and to stations."""

    try:
        from_station = handler.route_state.from_station
        to_station = handler.route_state.to_station

        if not from_station or not to_station:
            QMessageBox.information(
                handler.parent_dialog,
                "Missing Stations",
                "Please select both From and To stations first.",
            )
            return

        if hasattr(handler.parent_dialog, "fastest_route_button"):
            handler.parent_dialog.fastest_route_button.setEnabled(False)
            handler.parent_dialog.fastest_route_button.setText("Finding...")

        if hasattr(handler.parent_dialog, "route_info_widget"):
            handler.parent_dialog.route_info_widget.set_progress_message(
                "fastest_route",
                "Finding fastest route...",
            )

        QApplication.processEvents()

        from_parsed = handler.station_database.parse_station_name(from_station)
        to_parsed = handler.station_database.parse_station_name(to_station)

        departure_time = None
        if hasattr(handler.parent_dialog, "departure_time_picker") and not handler.parent_dialog.departure_time_picker.is_empty():
            departure_time = handler.parent_dialog.departure_time_picker.get_time()

        best_route = None
        try:
            routes = handler.station_database.find_route_between_stations(
                from_parsed,
                to_parsed,
                departure_time=departure_time,
            )
            if routes:
                best_route = min(routes, key=len)
                logger.debug("Found route via database manager: %s", " → ".join(best_route))
        except Exception as route_error:  # pragma: no cover
            logger.error("Database route finding failed: %s", route_error)

        if not best_route:
            best_route = handler._find_fastest_direct_route(from_parsed, to_parsed)
            if best_route:
                logger.debug("Found route via fallback: %s", " → ".join(best_route))

        if hasattr(handler.parent_dialog, "fastest_route_button"):
            handler.parent_dialog.fastest_route_button.setEnabled(True)
            handler.parent_dialog.fastest_route_button.setText("Fastest Route")

        if best_route:
            train_change_stations: list[str] = []
            try:
                train_change_stations = handler.station_database.identify_train_changes(best_route)
                logger.debug("Train changes identified: %s", train_change_stations)
            except Exception as exc:  # pragma: no cover
                logger.warning("Error identifying train changes: %s", exc)

            handler.route_state.set_via_stations(train_change_stations)
            handler.route_state.route_auto_fixed = True

            if hasattr(handler.parent_dialog, "route_info_widget"):
                handler.parent_dialog.route_info_widget.update_route_info(
                    from_station,
                    to_station,
                    train_change_stations,
                    True,
                )

            if train_change_stations:
                QMessageBox.information(
                    handler.parent_dialog,
                    "Fastest Route Found",
                    "Optimal route with %s train change(s):\n%s"
                    % (len(train_change_stations), " → ".join(best_route)),
                )
            else:
                QMessageBox.information(
                    handler.parent_dialog,
                    "Direct Route",
                    "Direct route is optimal:\n%s" % (" → ".join(best_route)),
                )

            handler.route_found.emit(best_route)
            return

        if hasattr(handler.parent_dialog, "route_info_widget"):
            handler.parent_dialog.route_info_widget.update_route_info(
                from_station,
                to_station,
                handler.route_state.via_stations,
                handler.route_state.route_auto_fixed,
            )

        QMessageBox.information(
            handler.parent_dialog,
            "No Route Found",
            "No optimal route could be found between the selected stations.",
        )

    except Exception as exc:  # pragma: no cover
        logger.error("Error finding fastest route: %s", exc)
        if hasattr(handler.parent_dialog, "fastest_route_button"):
            handler.parent_dialog.fastest_route_button.setEnabled(True)
            handler.parent_dialog.fastest_route_button.setText("Fastest Route")
        QMessageBox.critical(
            handler.parent_dialog,
            "Error",
            f"Failed to find fastest route: {exc}",
        )


def auto_fix_route_from_button(*, handler) -> None:
    """Auto-fix route when button is clicked."""

    try:
        from_station = handler.route_state.from_station
        to_station = handler.route_state.to_station

        if not from_station or not to_station:
            QMessageBox.information(
                handler.parent_dialog,
                "Missing Stations",
                "Please select both From and To stations first.",
            )
            return

        if hasattr(handler.parent_dialog, "auto_fix_route_button"):
            handler.parent_dialog.auto_fix_route_button.setEnabled(False)
            handler.parent_dialog.auto_fix_route_button.setText("Auto-Fixing...")

        if hasattr(handler.parent_dialog, "route_info_widget"):
            handler.parent_dialog.route_info_widget.set_progress_message(
                "auto_fix",
                "Auto-fixing route...",
            )

        QApplication.processEvents()

        from_parsed = handler.station_database.parse_station_name(from_station)
        to_parsed = handler.station_database.parse_station_name(to_station)

        departure_time = None
        if hasattr(handler.parent_dialog, "departure_time_picker") and not handler.parent_dialog.departure_time_picker.is_empty():
            departure_time = handler.parent_dialog.departure_time_picker.get_time()

        best_route = None
        try:
            routes = handler.station_database.find_route_between_stations(
                from_parsed,
                to_parsed,
                departure_time=departure_time,
            )
            if routes:
                best_route = routes[0]
                logger.debug(
                    "Auto-fix found route via database manager: %s",
                    " → ".join(best_route),
                )
        except Exception as exc:  # pragma: no cover
            logger.error("Database route finding failed: %s", exc)

        if not best_route:
            best_route = handler._find_simple_direct_route_fallback(from_parsed, to_parsed)
            if best_route:
                logger.debug(
                    "Auto-fix found route via fallback: %s",
                    " → ".join(best_route),
                )

        if hasattr(handler.parent_dialog, "auto_fix_route_button"):
            handler.parent_dialog.auto_fix_route_button.setEnabled(True)
            handler.parent_dialog.auto_fix_route_button.setText("Auto-Fix Route")

        if best_route:
            train_changes: list[str] = []
            try:
                train_changes = handler.station_database.identify_train_changes(best_route)
            except Exception as exc:  # pragma: no cover
                logger.warning("Error identifying train changes: %s", exc)

            handler.route_state.set_via_stations(train_changes)
            handler.route_state.route_auto_fixed = True

            if hasattr(handler.parent_dialog, "route_info_widget"):
                handler.parent_dialog.route_info_widget.update_route_info(
                    from_station,
                    to_station,
                    train_changes,
                    True,
                )

            if train_changes:
                QMessageBox.information(
                    handler.parent_dialog,
                    "Route Fixed",
                    "Route has been automatically fixed with %s train changes:\n%s"
                    % (len(train_changes), " → ".join(best_route)),
                )
            else:
                QMessageBox.information(
                    handler.parent_dialog,
                    "Route Fixed",
                    "Route has been fixed - direct connection is optimal.",
                )

            handler.route_optimization_completed.emit(
                True,
                "Route fixed successfully",
                best_route,
            )
            return

        if hasattr(handler.parent_dialog, "route_info_widget"):
            handler.parent_dialog.route_info_widget.update_route_info(
                from_station,
                to_station,
                handler.route_state.via_stations,
                handler.route_state.route_auto_fixed,
            )

        QMessageBox.warning(
            handler.parent_dialog,
            "Cannot Fix Route",
            "Unable to find a valid route between the selected stations.",
        )
        handler.route_optimization_completed.emit(False, "No valid route found", [])

    except Exception as exc:  # pragma: no cover
        logger.error("Error in auto_fix_route_from_button: %s", exc)
        if hasattr(handler.parent_dialog, "auto_fix_route_button"):
            handler.parent_dialog.auto_fix_route_button.setEnabled(True)
            handler.parent_dialog.auto_fix_route_button.setText("Auto-Fix Route")
        QMessageBox.critical(
            handler.parent_dialog,
            "Error",
            f"Failed to auto-fix route: {exc}",
        )

