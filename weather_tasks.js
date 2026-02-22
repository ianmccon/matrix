const axios = require('axios');
const fs = require('fs');
const path = require('path');
const NodeCache = require('node-cache');

const cache = new NodeCache({ stdTTL: 3600 }); // 1 hour default TTL

/**
 * Get weather data from PirateWeather API
 * @param {string} apiKey - PirateWeather API key
 * @param {number} latitude - Location latitude
 * @param {number} longitude - Location longitude
 * @returns {Promise<Array>} [currentWeather, forecastDays] or [null, null] on error
 */
async function getWeatherData(apiKey, latitude, longitude) {
  try {
    const cacheKey = 'weather_data';
    const cached = cache.get(cacheKey);
    if (cached) {
      return cached;
    }

    const cacheFile = path.join(__dirname, 'weather_cache.json');

    // Try reading from cache file first (written by background task)
    if (fs.existsSync(cacheFile)) {
      try {
        const cacheData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
        if (cacheData.current_weather && cacheData.forecast_days) {
          cache.set(cacheKey, [cacheData.current_weather, cacheData.forecast_days], 3600);
          return [cacheData.current_weather, cacheData.forecast_days];
        }
      } catch (e) {
        console.log('Could not read weather cache file, fetching live from PirateWeather...');
      }
    }

    // Fetch live from PirateWeather API
    const url = `https://api.pirateweather.net/forecast/${apiKey}/${latitude},${longitude}`;

    const response = await axios.get(url, {
      timeout: 10000,
      params: {
        units: 'uk2' // Use UK units (Celsius, m/s)
      }
    });

    if (response.status !== 200) {
      console.error('PirateWeather API request failed:', response.statusText);
      return [null, null];
    }

    const data = response.data;

    // Current weather: use current conditions
    const current = {
      time: data.currently?.time,
      temperature: data.currently?.temperature,
      summary: data.currently?.summary,
      icon: data.currently?.icon,
      humidity: data.currently?.humidity,
      windSpeed: data.currently?.windSpeed,
      feelsLike: data.currently?.apparentTemperature
    };

    // Forecast: next 7 days from daily data
    const forecastDays = [];
    if (data.daily && data.daily.data) {
      for (let i = 0; i < Math.min(7, data.daily.data.length); i++) {
        const day = data.daily.data[i];
        const dt = new Date(day.time * 1000); // Convert Unix timestamp to Date
        const weekday = dt.toLocaleDateString('en-US', { weekday: 'short' });

        forecastDays.push({
          day: {
            time: day.time,
            temperatureMax: day.temperatureMax,
            temperatureMin: day.temperatureMin,
            summary: day.summary,
            icon: day.icon,
            precipProbability: day.precipProbability,
            humidity: day.humidity,
            windSpeed: day.windSpeed
          },
          weekday
        });
      }
    }

    const result = [current, forecastDays];
    cache.set(cacheKey, result, 3600);

    // Also save to cache file for persistence
    try {
      fs.writeFileSync(cacheFile, JSON.stringify({
        current_weather: current,
        forecast_days: forecastDays,
        timestamp: new Date().toISOString()
      }, null, 2));
    } catch (e) {
      console.log('Could not write weather cache file:', e.message);
    }

    return result;

  } catch (error) {
    console.error('Error fetching weather from PirateWeather:', error.message);
    return [null, null];
  }
}

/**
 * Format temperature for display
 */
function formatTemperature(temp) {
  if (temp === null || temp === undefined) return 'N/A';
  return Math.round(temp) + '°C';
}

/**
 * Get weather icon/symbol mapping for PirateWeather icons
 */
function getWeatherIcon(iconName) {
  const iconMap = {
    'clear-day': '☀️',
    'clear-night': '🌙',
    'partly-cloudy-day': '⛅',
    'partly-cloudy-night': '🌤️',
    'cloudy': '☁️',
    'rain': '🌧️',
    'sleet': '🌨️',
    'snow': '❄️',
    'wind': '💨',
    'fog': '🌫️',
    'hail': '🧊',
    'thunderstorm': '⛈️'
  };
  return iconMap[iconName] || '🌡️';
}

module.exports = {
  getWeatherData,
  formatTemperature,
  getWeatherIcon
};
