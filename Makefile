.PHONY: build clean distclean

build:
	sudo docker compose up -d

clean:
	sudo docker compose down --rmi local

distclean:
	sudo docker compose down --rmi local -v
	sudo docker system prune -a --volumes -f
