# FLOTO Dashboard

## Dependencies

To run, you must install docker, docker-compose, and make.

## Configuration

Create a `.env` file:

`$ cp .env.sample .env`

Edit the variables as needed.

Create a `config/` directory with `keys` and `kube` as subdirectories. 

- `keys` should contain `id_rsa` and `id_rsa.pub`, which are used when running commands on the device.
- `kube` should contain a file `config`, which is the kubernetes config used to deploy applications.

## Developing

To build the images, first run:

`make build-dev`

and then start the containers

`make start`

Changes should be automatically reloaded. You can connect to the dashboard by
opening `http://localhost:8080` in your browser.

## Production deployment

See [dashboard-deploy](https://github.com/UChicago-FLOTO/dashboard-deploy)

## Admin

To gain access to the admin panel, set `is_superuser` on an existing user
via the database, or have an existing superuser set this via the admin panel.

