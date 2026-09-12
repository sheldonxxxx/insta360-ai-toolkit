// MediaSDK 3.1.5 still-photo helper. No CameraSDK, network, or source writes.
#include <ins_stitcher.h>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>
namespace fs = std::filesystem;

int main(int argc, char** argv) {
  try {
    if (argc == 1 || std::string(argv[1]) == "--help") {
      std::cout << "media_tool info --input FILE [--input FILE]\n"
                << "media_tool image --input FILE --output NEW.jpg --width 1920 --height 960\n"
                << "  --models DIR --log-dir DIR --stitch template|optflow|dynamicstitch|aistitch\n"
                << "  --cuda 0|1 --accel auto|cpu --accessory -1..20\n"
                << "  --flowstate 0|1 --fusion 0|1 --denoise 0|1 --cooling-shell 0|1\n"
                << "  --colorplus 0|1 --colorplus-strength FLOAT\n"
                << "  --exposure/--highlights/--shadows/--contrast/--brightness/--blackpoint\n"
                << "  --saturation/--vibrance/--warmth/--tint INT [-100,100]\n"
                << "  --definition INT [0,100]\n";
      return 0;
    }
    std::string mode = argv[1];
    if (mode != "info" && mode != "image") throw std::runtime_error("mode must be info or image");
    std::vector<std::string> inputs;
    std::map<std::string,std::string> opts;
    const std::vector<std::string> known = {"output","width","height","models","log-dir","stitch","cuda","accel","accessory","flowstate","fusion","denoise","cooling-shell","colorplus","colorplus-strength","exposure","highlights","shadows","contrast","brightness","blackpoint","saturation","vibrance","warmth","tint","definition"};
    for (int i=2;i<argc;i+=2) {
      if (i+1>=argc || std::string(argv[i]).rfind("--",0)!=0) throw std::runtime_error("expected --name value pairs");
      std::string key=std::string(argv[i]).substr(2), value=argv[i+1];
      if(key=="input") { inputs.push_back(fs::canonical(value).string()); continue; }
      if(std::find(known.begin(),known.end(),key)==known.end()) throw std::runtime_error("unknown option: "+key);
      if(!opts.emplace(key,value).second) throw std::runtime_error("duplicate option: "+key);
    }
    if(inputs.empty()) throw std::runtime_error("at least one input is required");
    if(std::set<std::string>(inputs.begin(),inputs.end()).size()!=inputs.size()) throw std::runtime_error("duplicate input file; HDR requires distinct bracket frames");
    for(auto& input:inputs) if(!fs::is_regular_file(input)) throw std::runtime_error("input is not a regular file");
    auto get=[&](std::string key,std::string fallback) { return opts.count(key)?opts.at(key):fallback; };
    auto integer=[&](std::string key,int fallback,int lo,int hi) {
      if(!opts.count(key)) return fallback;
      size_t n=0; int v=std::stoi(opts.at(key),&n);
      if(n!=opts.at(key).size() || v<lo || v>hi) throw std::runtime_error("out-of-range integer: "+key);
      return v;
    };
    auto flag=[&](std::string key) { return integer(key,0,0,1)==1; };
    auto extension=[](const fs::path& p) {
      auto e=p.extension().string(); std::transform(e.begin(),e.end(),e.begin(),[](unsigned char c){return std::tolower(c);}); return e;
    };
    std::string output;
    int width=0,height=0;
    std::string stitch=get("stitch","optflow"), accel=get("accel","auto");
    const std::map<std::string,ins::STITCH_TYPE> algorithms={{"template",ins::STITCH_TYPE::TEMPLATE},{"optflow",ins::STITCH_TYPE::OPTFLOW},{"dynamicstitch",ins::STITCH_TYPE::DYNAMICSTITCH},{"aistitch",ins::STITCH_TYPE::AIFLOW}};
    if(!algorithms.count(stitch)) throw std::runtime_error("invalid stitch algorithm");
    if(accel!="auto" && accel!="cpu") throw std::runtime_error("accel must be auto or cpu");
    int accessory=integer("accessory",-1,-1,20);
    float strength=0.3f;
    if(opts.count("colorplus-strength")) {
      size_t n=0; strength=std::stof(opts.at("colorplus-strength"),&n);
      if(n!=opts.at("colorplus-strength").size() || !std::isfinite(strength) || strength<0.0f || strength>1.0f) throw std::runtime_error("ColorPlus strength must be within the official guide range [0,1]");
    }
    const std::vector<std::string> controls={"exposure","highlights","shadows","contrast","brightness","blackpoint","saturation","vibrance","warmth","tint","definition"};
    std::map<std::string,int> values;
    for(auto& key:controls) values[key]=integer(key,0,key=="definition"?0:-100,100);
    for(auto& key:{"cuda","flowstate","fusion","denoise","cooling-shell","colorplus"}) flag(key);
    if(mode=="image") {
      if(inputs.size()==2) throw std::runtime_error("photo input count must be 1 or a distinct same-capture HDR bracket of at least 3 frames");
      for(auto& input:inputs) { auto e=extension(input); if(e!=".insp" && e!=".jpg" && e!=".jpeg" && e!=".dng") throw std::runtime_error("photo input must be INSP/JPEG/DNG; confirm native geometry and metadata first"); }
      if(!opts.count("output")) throw std::runtime_error("new output path is required");
      output=fs::absolute(opts.at("output")).lexically_normal().string();
      if(extension(output)!=".jpg" && extension(output)!=".jpeg") throw std::runtime_error("photo helper output must be JPEG");
      if(fs::symlink_status(output).type()!=fs::file_type::not_found) throw std::runtime_error("output already exists; choose a new path");
      if(!fs::is_directory(fs::path(output).parent_path())) throw std::runtime_error("create the output parent directory first");
      width=integer("width",1920,2,65536); height=integer("height",960,2,65536);
      if(width!=2*height) throw std::runtime_error("this helper preserves full-sphere output at 2:1; reframing is a separate operation");
      if(flag("fusion") && stitch=="template") throw std::runtime_error("stitch fusion is incompatible with template stitching");
      if((stitch=="aistitch" || flag("denoise") || flag("colorplus") || flag("cooling-shell")) && !opts.count("models")) throw std::runtime_error("model-backed processing needs --models");
    }
    if(opts.count("models") && !fs::is_directory(opts.at("models"))) throw std::runtime_error("model directory is missing");
    if(opts.count("log-dir") && !fs::is_directory(opts.at("log-dir"))) throw std::runtime_error("log directory is missing");
    std::string log_file;
    if(opts.count("log-dir")) {
      log_file=(fs::absolute(opts.at("log-dir"))/"media-sdk.log").string();
      if(fs::symlink_status(log_file).type()!=fs::file_type::not_found) throw std::runtime_error("SDK log already exists; choose a fresh job directory");
    }
    // Validation above runs before entering the proprietary runtime.
    // Some SDK components printf to stdout, including during process shutdown.
    // Keep the public result stream separate so SDK logs cannot corrupt JSON.
    FILE* result_stream=fdopen(dup(STDOUT_FILENO),"w");
    if(!result_stream || dup2(STDERR_FILENO,STDOUT_FILENO)<0) throw std::runtime_error("cannot isolate SDK log stream");
    auto report=[&](const std::string& json) { fprintf(result_stream,"%s\n",json.c_str()); fflush(result_stream); };
    ins::InitEnv();
    ins::SetLogLevel(ins::InsLogLevel::INFO);
    // Despite the header's 'directory' comment, this build requires a file path.
    if(!log_file.empty()) ins::SetLogPath(log_file);
    if(opts.count("models")) ins::SetModelFileRootDir(fs::absolute(opts.at("models")).string()+"/");
    std::cerr << "MediaSDK version=" << ins::GetVersion() << " major=" << ins::GetVersionMajor() << "\n";
    if(mode=="info") {
      ins::MediaFileInfo info{};
      bool ok=ins::GetMediaFileInfo(inputs,info);
      if(!ok) { report("{\"ok\":false,\"sdk_parse_ok\":false}"); return 3; }
      const bool valid=info.width>0 && info.height>0;
      std::ostringstream result;
      result << "{\"ok\":" << (valid?"true":"false") << ",\"sdk_parse_ok\":true,\"media_type\":" << static_cast<int>(info.media_type)
                << ",\"width\":" << info.width << ",\"height\":" << info.height
                << ",\"fps\":" << info.fps << ",\"bitrate\":" << info.bitrate << ",\"duration_ms\":" << info.duration_ms << "}";
      report(result.str());
      return valid?0:5;
    }
    ins::ImageStitcher s;
    s.SetInputPath(inputs); s.SetOutputPath(output); s.SetOutputSize(width,height);
    s.SetStitchType(algorithms.at(stitch)); s.EnableCuda(flag("cuda"));
    s.SetImageProcessingAccelType(accel=="cpu"?ins::ImageProcessingAccel::kCPU:ins::ImageProcessingAccel::kAuto);
    s.SetCameraAccessoryType(static_cast<ins::CameraAccessoryType>(accessory));
    s.EnableFlowState(flag("flowstate")); s.EnableStitchFusion(flag("fusion"));
    s.EnableDenoise(flag("denoise")); s.EnableCoolingShellDetection(flag("cooling-shell"));
    s.EnableColorPlus(flag("colorplus"),strength);
    s.SetExposure(values["exposure"]); s.SetHighlights(values["highlights"]); s.SetShadows(values["shadows"]);
    s.SetContrast(values["contrast"]); s.SetBrightness(values["brightness"]); s.SetBlackpoint(values["blackpoint"]);
    s.SetSaturation(values["saturation"]); s.SetVibrance(values["vibrance"]); s.SetWarmth(values["warmth"]);
    s.SetTint(values["tint"]); s.SetDefinition(values["definition"]);
    bool ok=s.Stitch();
    if(!ok || !fs::is_regular_file(output) || fs::file_size(output)==0) {
      std::cerr << "Stitch failed or output absent; inspect logs and any partial output before retrying.\n"; return 4;
    }
    report("{\"ok\":true,\"bytes\":"+std::to_string(fs::file_size(output))+",\"visual_review_required\":true}");
    return 0;
  } catch(const std::exception& e) { std::cerr << "media_tool: " << e.what() << "\n"; return 2; }
}
