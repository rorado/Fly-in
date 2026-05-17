from config import Config


class Graph:
    def __init__(self, conf: Config):
        self.config: Config = conf
        self.adj: dict[str, list[str]] = {}
        self._build(conf)

    def _build(self, conf: Config) -> None:

        if conf.start_hub and conf.start_hub.value:
            start_name = conf.start_hub.value.name
            self.adj[start_name] = self.get_neighbors(start_name)

        if conf.end_hub and conf.end_hub.value:
            end_name = conf.end_hub.value.name
            self.adj[end_name] = self.get_neighbors(end_name)

        if conf.hubs:
            for hub in conf.hubs.keys():
                self.adj[hub] = self.get_neighbors(hub)

    def get_neighbors(self, hub: str = "") -> list[str]:
        ft: list[str] = []

        if self.config.connections:
            for cnvl in self.config.connections.values():

                if not cnvl.value:
                    continue

                if cnvl.value.from_hub == hub and cnvl.value.to_hub:
                    ft.append(cnvl.value.to_hub)

                elif cnvl.value.to_hub == hub and cnvl.value.from_hub:
                    ft.append(cnvl.value.from_hub)

        return ft

    def display_adj(self) -> None:
        for i, value in self.adj.items():
            print(i, ":", value)
