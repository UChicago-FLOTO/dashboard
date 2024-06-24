# FLOTO Dashboard + API

For documentation on using the dashboard, see our [docs](https://github.com/UChicago-FLOTO/docs/blob/master/README.md).


## Local Development

You can locally run our docker-compose file (see the next section), which will configure several containers:
- *floto_web* - serves the frontend web app, and the REST API
- *floto_db* - a mysql database, used by the web backend
- *floto_tasks* - runs background tasks for the backend
- *redis* - used by the background tasks

The *floto_web* container uses django's `runserver` for development, which automatically reloads when changes are made to files under `floto/`.

Updating dependencies/environment variables require the container to be rebuild/restarted.

The frontend webapp uses Vue.js. For simplicity, [Vue is used directly from CDN](https://vuejs.org/guide/quick-start.html#using-vue-from-cdn). Changes to the frontend will be reloaded when the browser is refreshed. 

### Dependencies

You must install docker with docker-compose, and Make.

### Configuration

Create a `.env` file:

`$ cp .env.sample .env`

Edit the variables as needed.

Create a `config/` directory with `keys` and `kube` as subdirectories. 

- `keys` should contain `id_rsa` and `id_rsa.pub`, which are used when running commands on the device.
- `kube` should contain a file `config`, which is the kubernetes config used to deploy applications.

## Building

To build the images, first run: `make build-dev`

Then start the containers: `make start`

To initialize the database: `make migrations`

You can connect to the dashboard by opening `http://localhost:8080` in your browser.

## Production deployment

See [dashboard-deploy](https://github.com/UChicago-FLOTO/dashboard-deploy)

## Admin

To gain access to the admin panel, set `is_superuser` on an existing user
via the database, or have an existing superuser set this via the admin panel.

