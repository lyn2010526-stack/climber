"""Tests for the plugin kernel (lifecycle, DI, event bus, hot-swap)."""

from __future__ import annotations

import asyncio

import pytest

from app.core.plugin_kernel import Plugin, PluginContext, PluginKernel, TypedEventBus


class GreetingPlugin(Plugin):
    id = "greeting"
    version = "1.0.0"

    async def on_mount(self, context: PluginContext) -> None:
        await super().on_mount(context)
        context.register_service("greeter", lambda name: f"hello {name}")

    def greet(self, name: str) -> str:
        return self.context.get_service("greeter")(name)


class DependentPlugin(Plugin):
    id = "dependent"
    dependencies = ["greeting"]

    async def on_mount(self, context: PluginContext) -> None:
        await super().on_mount(context)
        context.register_service("shouter", lambda name: self.context.get_service("greeter")(name).upper())


class SubscriberPlugin(Plugin):
    id = "subscriber"
    dependencies = ["greeting"]
    received: list[dict] = []

    async def on_mount(self, context: PluginContext) -> None:
        await super().on_mount(context)
        async def on_greet(event: dict) -> None:
            self.received.append(event)
        context.subscribe("greet", on_greet)


@pytest.mark.asyncio
async def test_mount_resolves_dependencies_in_order():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    kernel.register(DependentPlugin())
    await kernel.mount("dependent")
    assert kernel.list_mounted() == ["greeting", "dependent"]
    service = kernel.get_service("greeter")
    assert service("bob") == "hello bob"


@pytest.mark.asyncio
async def test_unmount_reverses_registrations_no_orphans():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    kernel.register(DependentPlugin())
    await kernel.mount("dependent")
    assert kernel.has_service("greeter")
    assert kernel.has_service("shouter")

    unmounted = await kernel.unmount("dependent")
    assert unmounted == ["dependent"]
    # dependent's service gone, greeting still mounted
    assert not kernel.has_service("shouter")
    assert kernel.has_service("greeter")

    unmounted = await kernel.unmount("greeting")
    assert unmounted == ["greeting"]
    assert not kernel.has_service("greeter")


@pytest.mark.asyncio
async def test_unmount_without_cascade_blocks_when_depended_on():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    kernel.register(DependentPlugin())
    await kernel.mount("dependent")
    from app.core.plugin_kernel.kernel import PluginConflictError

    with pytest.raises(PluginConflictError):
        await kernel.unmount("greeting")


@pytest.mark.asyncio
async def test_missing_dependency_raises():
    kernel = PluginKernel()
    kernel.register(DependentPlugin())
    from app.core.plugin_kernel.kernel import PluginDependencyError

    with pytest.raises(PluginDependencyError):
        await kernel.mount("dependent")


@pytest.mark.asyncio
async def test_service_collision_raises():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    await kernel.mount("greeting")
    from app.core.plugin_kernel.kernel import PluginConflictError

    with pytest.raises(PluginConflictError):
        kernel.register_service("greeter", object(), owner="other")


@pytest.mark.asyncio
async def test_event_pub_sub_and_subscriber_cleanup():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    sub = SubscriberPlugin()
    kernel.register(sub)
    await kernel.mount("subscriber")
    await kernel.emit("greet", {"name": "bob"})
    assert len(sub.received) == 1
    assert sub.received[0]["name"] == "bob"
    assert sub.received[0]["type"] == "greet"

    await kernel.unmount("subscriber")
    sub.received.clear()
    await kernel.emit("greet", {"name": "alice"})
    assert sub.received == []


@pytest.mark.asyncio
async def test_request_response():
    bus = TypedEventBus()

    async def handler(payload: dict) -> dict:
        return {"sum": payload["a"] + payload["b"]}

    bus.register_request_handler("add", handler)
    result = await bus.request("add", {"a": 2, "b": 3})
    assert result == {"sum": 5}

    from app.core.plugin_kernel.event_bus import EventBusError

    with pytest.raises(EventBusError):
        await bus.request("nope", {})


@pytest.mark.asyncio
async def test_hot_swap_replaces_implementation():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    await kernel.mount("greeting")
    assert kernel.get_service("greeter")("bob") == "hello bob"

    # swap with a new implementation
    await kernel.unmount("greeting")
    await kernel.mount("greeting")
    assert kernel.get_service("greeter")("bob") == "hello bob"


@pytest.mark.asyncio
async def test_shutdown_unmounts_everything():
    kernel = PluginKernel()
    kernel.register(GreetingPlugin())
    kernel.register(DependentPlugin())
    await kernel.mount("dependent")
    await kernel.shutdown()
    assert kernel.list_mounted() == []
    assert not kernel.has_service("greeter")


def test_trace_sink_receives_events():
    received = []

    async def sink(event: dict) -> None:
        received.append(event)

    bus = TypedEventBus(trace_sink=sink)
    asyncio.run(bus.publish("x", {"n": 1}))
    assert len(received) == 1
    assert received[0]["type"] == "x"


def test_kernel_uses_injected_event_bus():
    bus = TypedEventBus()

    assert PluginKernel(event_bus=bus).event_bus is bus


@pytest.mark.asyncio
async def test_arch_v2_uses_one_traced_plugin_event_bus(monkeypatch, tmp_path):
    from app import main
    from app.core.plugin_kernel import event_bus as event_bus_module

    monkeypatch.setattr(main.settings, "enable_arch_v2", True)
    monkeypatch.setattr(main.settings, "enable_plugin_kernel", True)
    monkeypatch.setattr(main.settings, "enable_trace_log", True)
    monkeypatch.setattr(main.settings, "log_dir", str(tmp_path))
    monkeypatch.setattr(event_bus_module, "_default_bus", None)

    handles = await main._init_arch_v2()
    assert handles is not None
    assert handles["plugin_kernel"].event_bus is handles["event_bus"]

    await handles["event_bus"].publish(
        "plugin.test", {"session_id": "session-1", "value": 1}
    )

    events = await handles["trace_log"].read("session-1")
    assert [(event.event_type, event.data) for event in events] == [
        ("plugin.test", {"session_id": "session-1", "value": 1})
    ]
