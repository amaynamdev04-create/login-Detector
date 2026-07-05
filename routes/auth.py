"""Authentication routes for demo login attempts."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from services.authentication import (
    authenticate_user,
    format_block_time,
    get_active_block,
    get_client_network,
    write_login_event,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render and process the built-in login form."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        client_network = get_client_network(request)
        active_block = get_active_block(client_network.public_ip)
        if active_block:
            write_login_event(
                username=username or "unknown",
                client_network=client_network,
                success=False,
                log_file_path=current_app.config["LOG_FILE_PATH"],
                source=current_app.config["DEFAULT_EVENT_SOURCE"],
                request=request,
            )
            flash(
                f"Login blocked for {client_network.public_ip} until {format_block_time(active_block.expires_at)}.",
                "error",
            )
            return render_template("login.html", blocked=True)

        user = authenticate_user(username=username, password=password)
        success = user is not None
        write_login_event(
            username=username or "unknown",
            client_network=client_network,
            success=success,
            log_file_path=current_app.config["LOG_FILE_PATH"],
            source=current_app.config["DEFAULT_EVENT_SOURCE"],
            request=request,
        )

        if not success:
            flash("Invalid username or password.", "error")
            return render_template("login.html", blocked=False)

        session["user_id"] = user.id
        session["username"] = user.username
        session["full_name"] = user.full_name
        session["role"] = user.role
        flash(f"Signed in successfully as {user.full_name}.", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html", blocked=False)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear the active analyst session."""
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
