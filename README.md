# FLOTO Dashboard

## Dependencies

To run, you must install docker, docker-compose, and make.

## Configuration

Create a `.env` file:

`$ cp .env.sample .env`

Edit the variables as needed.

## Developing

To build the images, first run:

`make build-dev`

and then start the containers

`make start`

Changes should be automatically reloaded. You can connect to the dashboard by
opening `http://localhost:8080` in your browser.

## Deployment

See [dashboard-deploy](https://github.com/UChicago-FLOTO/dashboard-deploy)
