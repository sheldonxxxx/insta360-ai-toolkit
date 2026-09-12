// Read-only InsMetaDataSDK 2.0.2 probe. Build against its include/ and lib/.
// No output files are created; JSON goes to stdout. Exact native timestamps
// are strings so downstream JavaScript cannot silently round int64 values.
#include <metaData.h>

#include <exception>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>

namespace {
// The proprietary Linux library writes diagnostics with printf to stdout.
// Keep them on stderr while all SDK objects are alive, including destruction.
class SdkStdoutToStderr {
 public:
    SdkStdoutToStderr() {
        std::cout.flush();
        std::fflush(stdout);
        saved_ = ::dup(STDOUT_FILENO);
        if (saved_ < 0) throw std::runtime_error("Cannot save stdout");
        if (::dup2(STDERR_FILENO, STDOUT_FILENO) < 0) {
            ::close(saved_);
            saved_ = -1;
            throw std::runtime_error("Cannot redirect SDK diagnostics to stderr");
        }
    }
    ~SdkStdoutToStderr() {
        std::cout.flush();
        std::fflush(stdout);
        if (saved_ >= 0) {
            ::dup2(saved_, STDOUT_FILENO);
            ::close(saved_);
        }
    }
    SdkStdoutToStderr(const SdkStdoutToStderr&) = delete;
    SdkStdoutToStderr& operator=(const SdkStdoutToStderr&) = delete;
 private:
    int saved_ = -1;
};

std::string quote(const std::string& value) {
    std::ostringstream out;
    out << '"';
    const char* hex = "0123456789abcdef";
    for (unsigned char c : value) {
        switch (c) {
            case '"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (c < 0x20) out << "\\u00" << hex[c >> 4] << hex[c & 15];
                else out << static_cast<char>(c);
        }
    }
    out << '"';
    return out.str();
}

const char* boolean(bool value) { return value ? "true" : "false"; }

template <typename Item, typename Timestamp>
void streamSummary(const char* key, const char* method, bool succeeded,
                   const std::vector<Item>& items, Timestamp timestamp,
                   const char* units) {
    std::cout << "    " << quote(key) << ": {\"method\": " << quote(method)
              << ", \"ok\": " << boolean(succeeded)
              << ", \"count\": " << items.size()
              << ", \"timestamp_units\": " << quote(units)
              << ", \"first_timestamp_raw\": ";
    if (items.empty()) std::cout << "null";
    else std::cout << quote(std::to_string(timestamp(items.front())));
    std::cout << ", \"last_timestamp_raw\": ";
    if (items.empty()) std::cout << "null";
    else std::cout << quote(std::to_string(timestamp(items.back())));
    std::cout << "}";
}
}  // namespace

int main(int argc, char** argv) {
    std::string input;
    bool include_serial = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--include-serial") include_serial = true;
        else if (input.empty() && arg != "--help" && arg != "-h") input = arg;
        else {
            std::cerr << "Usage: metadata_probe [--include-serial] <input.insp|input.insv>\n";
            return arg == "--help" || arg == "-h" ? 0 : 2;
        }
    }
    if (input.empty()) {
        std::cerr << "Usage: metadata_probe [--include-serial] <input.insp|input.insv>\n";
        return 2;
    }

    try {
        bool parsed = false;
        bool gps_ok = false, gyro_ok = false, exposure_ok = false, timelapse_ok = false;
        int64_t first_timestamp = 0;
        std::string firmware, camera, serial;
        std::vector<GpsDataItem_t> gps;
        std::vector<GyroDataItem_t> gyro;
        std::vector<ExposureDataItem_t> exposure;
        std::vector<RawTimelapseItem_t> timelapse;
        {
            SdkStdoutToStderr diagnostics;
            ins_metadata::MetaDataParser parser;
            parsed = parser.Parse(input);
            if (parsed) {
                gps_ok = parser.GetGPSData(gps);
                gyro_ok = parser.GetGyroData(gyro);
                exposure_ok = parser.GetExposureData(exposure);
                timelapse_ok = parser.GetTimelapsePtsData(timelapse);
                first_timestamp = parser.GetFirstTimeStamp();
                firmware = parser.GetFireWareVersion();
                camera = parser.GetCameraType();
                serial = parser.GetSerialNumber();
            }
        }
        if (!parsed) {
            std::cout << "{\"schema_version\": 1, \"input\": " << quote(input)
                      << ", \"parse_ok\": false, \"error\": \"Parse returned false\"}\n";
            return 1;
        }

        std::cout << "{\n  \"schema_version\": 1,\n  \"input\": " << quote(input)
                  << ",\n  \"parse_ok\": true,\n  \"camera_type\": " << quote(camera)
                  << ",\n  \"firmware_version\": " << quote(firmware)
                  << ",\n  \"serial_number_included\": " << boolean(include_serial);
        if (include_serial) std::cout << ",\n  \"serial_number\": " << quote(serial);
        std::cout << ",\n  \"first_timestamp_ms_raw\": "
                  << quote(std::to_string(first_timestamp)) << ",\n  \"streams\": {\n";
        streamSummary("gps", "GetGPSData", gps_ok, gps,
                      [](const GpsDataItem_t& item) { return item.timestampMs; },
                      "unresolved: field timestampMs conflicts with seconds comment");
        std::cout << ",\n";
        streamSummary("gyro", "GetGyroData", gyro_ok, gyro,
                      [](const GyroDataItem_t& item) { return item.timestamp; },
                      "not specified in common.h");
        std::cout << ",\n";
        streamSummary("exposure", "GetExposureData", exposure_ok, exposure,
                      [](const ExposureDataItem_t& item) { return item.timestamp; },
                      "milliseconds per common.h");
        std::cout << ",\n";
        streamSummary("timelapse", "GetTimelapsePtsData", timelapse_ok, timelapse,
                      [](const RawTimelapseItem_t& item) { return item.timestamp; },
                      "milliseconds per common.h");
        std::cout << "\n  }\n}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cout << "{\"schema_version\": 1, \"input\": " << quote(input)
                  << ", \"error\": " << quote(error.what()) << "}\n";
        return 1;
    }
}
