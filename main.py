import os, random, json, uuid, shutil, copy
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# =====================================================
# ⚙️ INTERVIEW CONFIGURATION
# =====================================================
INTERVIEW_CONFIG = {
    "interview_name": "Data Annotation Interview — Round 1",
    "time_limit_minutes": 40,
    "task_count_image": 25,
    "task_count_video": 15,
    "task_count_other": 15
}

# =====================================================
# 📦 OBJECT DATABASE
# =====================================================
OBJECTS_DB = [
    {"id": 1, "name": "Chair",    "attributes": "Wooden, curved backrest, brown color, classic design"},
    {"id": 2, "name": "Stool",    "attributes": "Metal frame, minimalist, grey cushion, industrial look"},
    {"id": 3, "name": "Vase",     "attributes": "Glazed finish, round body, decorative patterns"},
    {"id": 4, "name": "Bottle",   "attributes": "Transparent, tall neck, smooth surface"},
    {"id": 5, "name": "Laptop",   "attributes": "Silver aluminum body, 15-inch screen, backlit keyboard"},
    {"id": 6, "name": "Phone",    "attributes": "Black glass back, 6.1-inch display, triple camera"},
    {"id": 7, "name": "Mug",      "attributes": "Ceramic, cylindrical, heat-resistant handle, various colors"},
    {"id": 8, "name": "Backpack", "attributes": "Nylon fabric, multiple zippers, padded straps"},
    {"id": 9, "name": "Lamp",     "attributes": "Metallic arm, adjustable neck, warm LED light"},
    {"id": 10, "name": "Sneakers", "attributes": "White mesh upper, rubber sole, lace-up, athletic style"},
]

IMAGE_MAPPING = {
    "Chair": "Chair", "Stool": "Stool", "Vase": "Vase", "Bottle": "Bottle",
    "Laptop": "Laptop", "Phone": "Phone", "Mug": "Mug", "Backpack": "Backpack",
    "Lamp": "Lamp", "Sneakers": "Sneakers",
}

# =====================================================
# 🎥 VIDEO SCENARIO DATABASE
# =====================================================
VIDEO_SCENARIOS_DB = [
    {
        "id": 1,
        "title": "Cyclists by the Marina",
        "description": "A 15-second clip showing a man cycling in front, followed closely by a woman with a backpack. They are riding along a paved path next to a marina with boats.",
        "frames": ["/images/cycle_1.jpg", "/images/cycle_2.jpg", "/images/cycle_3.jpg"],
        "questions": [
            "If you are tracking the man (Cyclist_A) across frames, what visual features would you use to ensure the model doesn't swap his ID with the woman (Cyclist_B) when they cross paths?",
            "Describe the action sequence occurring between Frame 1 and Frame 3 (e.g., pedaling, steering).",
            "If the man's front tire goes out of the frame in the next second, how do you handle the bounding box for the bicycle? Do you shrink the box or keep it anchored to the visible part?",
            "What is the precise moment the 'action' of passing the boat begins and ends?",
            "If the camera pans to the right in Frame 3, how would you ensure the tracking IDs remain consistent?",
            "Look at the background. How would you classify the boats in the marina - are they part of the background scene or independent objects that need bounding boxes?",
            "If a seagull flies across the screen in Frame 2, should it be annotated as an object of interest, or ignored as background noise?",
            "How would you annotate the shadows cast by the cyclists on the pavement?",
            "If the woman's backpack bounces significantly between frames, how do you maintain the bounding box around it?",
            "Describe how you would handle the annotation if the two cyclists crash into each other in the next second."
        ]
    },
    {
        "id": 2,
        "title": "Fruit Market Interaction",
        "description": "A 15-second clip of a buyer at a fruit market. The buyer reaches out, picks up an apple, inspects it, and places it in a basket.",
        "frames": ["/images/fruit_1.jpg", "/images/fruit_2.jpg", "/images/fruit_3.jpg"],
        "questions": [
            "Describe the action sequence occurring between Frame 1 and Frame 3 (e.g., reaching, grasping, inspecting, placing).",
            "If the buyer's hand covers the apple in Frame 2, how do you decide whether to label the apple as 'occluded' or 'invisible'?",
            "How would you distinguish the specific apple the buyer picks up from the other identical apples in the background stack?",
            "What is the precise moment the 'action' of picking up the fruit begins and ends?",
            "If the buyer drops the apple and it rolls away, how would you track its movement across the remaining frames?",
            "If the client wants you to track the basket as well, where should the bounding box be drawn in Frame 3?",
            "How would you annotate the hand of the buyer - as a whole bounding box, or individual keypoints for each finger?",
            "If another customer walks behind the buyer in Frame 2, should they be annotated?",
            "How do you handle the annotation if the buyer places the apple back on the stack instead of in the basket?",
            "If the lighting causes a glare on the apple in Frame 1, how does that affect your object detection annotation?"
        ]
    },
    {
        "id": 3,
        "title": "Driver Drowsiness Monitoring",
        "description": "An in-cabin camera view of a driver. Over the 15-second clip, the driver's eyes begin to close, and their head nods slightly downward.",
        "frames": ["/images/driver_1.jpg", "/images/driver_2.jpg", "/images/driver_3.jpg"],
        "questions": [
            "How would you annotate the transition from a normal blink in Frame 1 to prolonged eye closure in Frame 3?",
            "If the driver's hand covers their mouth while yawning in Frame 2, how do you handle the facial landmark annotations for the mouth?",
            "What specific visual features in these frames indicate fatigue, and how would you label them for a Driver Monitoring System?",
            "Describe the movement of the driver's head between Frame 1 and Frame 3.",
            "If the lighting changes significantly in Frame 3 (e.g., driving into a tunnel), how does that affect your ability to track the driver's gaze?",
            "Should the steering wheel be annotated in every frame, or only when the driver's hands are interacting with it?",
            "How would you annotate the driver's eye state in Frame 2 - as 'open', 'half-closed', or 'closed'?",
            "If the driver looks away from the road to check the rearview mirror in Frame 1, how should that be labeled?",
            "What is the best bounding box shape for the driver's face - a standard rectangle, or a polygon following the jawline?",
            "If the camera is slightly misaligned and cuts off the top of the driver's head in Frame 3, how do you annotate the visible portion?"
        ]
    },
    {
        "id": 4,
        "title": "Warehouse Robotics",
        "description": "A 15-second clip showing a robotic arm picking up a cardboard box from a conveyor belt and moving it to a stack.",
        "frames": ["/images/robot_1.jpg", "/images/robot_2.jpg", "/images/robot_3.jpg"],
        "questions": [
            "How would you draw the bounding box for the robotic arm - around the entire arm, or just the gripper mechanism?",
            "Describe the action occurring between Frame 1 and Frame 3.",
            "If the cardboard box is partially crushed or deformed in Frame 2, how does that affect your annotation?",
            "What is the precise moment the robotic gripper makes contact with the box?",
            "If the conveyor belt is moving continuously, how do you handle the tracking ID of the box before the robot picks it up?",
            "How would you annotate the conveyor belt itself - is it a single object, or background?",
            "If another box enters the frame in the background, should you annotate it even though the robot isn't interacting with it?",
            "How do you define the boundary between the robot's gripper and the box when they are touching?",
            "If the robot drops the box in Frame 3, how do you annotate the failure event?",
            "What visual features would you use to distinguish the cardboard box from the metal parts of the robot arm?"
        ]
    },
    {
        "id": 5,
        "title": "Retail Shelf Stocking",
        "description": "A 15-second clip of a store worker restocking a shelf with cereal boxes.",
        "frames": ["/images/shelf_1.jpg", "/images/shelf_2.jpg", "/images/shelf_3.jpg"],
        "questions": [
            "How would you annotate the worker's hands as they move boxes from a cart to the shelf?",
            "Describe the spatial relationship between the box in the worker's hand and the boxes already on the shelf in Frame 2.",
            "If the worker blocks the view of the shelf in Frame 2, how do you track the specific shelf slot they are filling?",
            "What is the precise moment the 'action' of stocking the shelf begins and ends?",
            "If a customer walks past in the background of Frame 3, should they be annotated for a retail analytics model?",
            "How would you label the empty space on the shelf in Frame 1?",
            "If the cereal box has text on it, should you annotate the text for OCR, or just the bounding box of the box?",
            "How do you handle the annotation if the worker drops a box in the next second?",
            "If the worker is wearing gloves, does that change how you annotate their hands?",
            "How would you distinguish between the different brands of cereal boxes on the shelf in Frame 3?"
        ]
    }
]

# =====================================================
# 🔍 ANNOTATION SCENARIO DATABASE
# =====================================================
ANNOTATION_SCENARIOS_DB = [
    {
        "id": 1,
        "title": "QA Review: Cyclist Annotation",
        "description": "Review the following annotated image. The bounding boxes were drawn by a junior annotator.",
        "image": "/images/annotated_cyclists.jpg",
        "questions": [
            "Look closely at the green bounding box (Cyclist_A). Does it fully encompass the entire bicycle and rider? If not, what is missing?",
            "The blue bounding box (Cyclist_B) is overlapping the green box. In a multi-object tracking scenario, is this acceptable? Why or why not?",
            "If the client's guidelines state 'Bounding boxes must contain the entire object including all wheels', would you approve or reject this annotation?",
            "Look at the background. The annotator missed the boat on the left. Should the boat have been annotated based on this scene context?",
            "Rate the overall quality of this annotation on a scale of 1-5 and explain your reasoning."
        ]
    }
]

# =====================================================
# 🖼️ IMAGES
# =====================================================
@app.get("/images/{filename}")
def get_image(filename: str):
    for ext in ['.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG']:
        path = f"images/{filename.split('.')[0]}{ext}"
        if os.path.exists(path):
            return FileResponse(path)
    return {"error": "Image not found"}

def get_random_image_for_object(name, rng=None):
    prefix = IMAGE_MAPPING.get(name, name)
    folder = "images"
    if not os.path.exists(folder): return None
    files = os.listdir(folder)
    matching = [f for f in files if f.lower().startswith(prefix.lower()) and f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if matching:
        picker = rng if rng else random
        return f"/images/{picker.choice(matching)}"
    return None

# =====================================================
# 🤖 QUESTION GENERATORS
# =====================================================
def generate_questions_for_pair(obj_a, obj_b):
    categories = {
        "colorful": [
            f"What is the dominant color of the {obj_a['name']} in the image?",
            f"Does the {obj_a['name']} have any patterns or prints? Describe what you see.",
            f"Which object in the image has more vibrant colors - the {obj_a['name']} or the {obj_b['name']}?",
            f"Describe the surface finish of the {obj_a['name']} (glossy, matte, textured, smooth).",
            f"Is the {obj_a['name']} in the image a single color or multi-colored?",
        ],
        "tech": [
            f"What material does the {obj_a['name']} appear to be made of (metal, plastic, glass)?",
            f"Does the {obj_a['name']} in the image look new, used, or worn?",
            f"Which object appears more modern - the {obj_a['name']} or the {obj_b['name']}?",
            f"How many visible buttons or ports can you see on the {obj_a['name']}?",
            f"Describe the color and finish of the {obj_a['name']} in the image.",
        ],
        "apparel": [
            f"What color is the main body of the {obj_a['name']} in the image?",
            f"Is the {obj_a['name']} in the image showing any visible wear, stains, or damage?",
            f"Which object looks more suitable for daily use - the {obj_a['name']} or the {obj_b['name']}?",
            f"Describe the material texture of the {obj_a['name']} (smooth, rough, soft, hard).",
            f"Are there any logos, labels, or branding visible on the {obj_a['name']}?",
        ],
        "furniture": [
            f"What color is the {obj_a['name']} in the image?",
            f"Describe the shape of the {obj_a['name']} - is it curved, straight, angular, or round?",
            f"Which object appears larger in the image - the {obj_a['name']} or the {obj_b['name']}?",
            f"What material does the {obj_a['name']} appear to be made of?",
            f"Which object looks more comfortable to use?",
        ],
        "default": [
            f"Describe the shape of the {obj_a['name']} in the image in one word.",
            f"Which object appears larger in the image - the {obj_a['name']} or the {obj_b['name']}?",
            f"Which object looks more durable?",
            f"What is the primary color of the {obj_a['name']}?",
            f"How does the {obj_a['name']} differ visually from the {obj_b['name']}?",
        ]
    }
    colorful = ["Vase", "Mug", "Backpack"]
    tech = ["Laptop", "Phone", "Lamp"]
    apparel = ["Sneakers", "Backpack"]
    furniture = ["Chair", "Stool"]

    pool = None
    for name in [obj_a["name"], obj_b["name"]]:
        if name in colorful: pool = categories["colorful"]; break
        if name in tech: pool = categories["tech"]; break
        if name in apparel: pool = categories["apparel"]; break
        if name in furniture: pool = categories["furniture"]; break
    if pool is None: pool = categories["default"]

    selected = random.sample(pool, 3)
    return {"q1": selected[0], "q2": selected[1], "q3": selected[2]}

def generate_questions_for_role(obj_a, obj_b, role):
    if role == "project-manager":
        pool = [
            f"Estimate how many annotators you would need to label 10,000 images of the {obj_a['name']} in 3 days.",
            f"What is the biggest risk to delivering a high-quality dataset for the {obj_a['name']} on time?",
            f"If the client changes the guidelines for the {obj_a['name']} halfway through the project, what is your action plan?",
            f"How would you write the training material to help annotators distinguish between the {obj_a['name']} and the {obj_b['name']}?",
            f"What quality metric would you track to ensure the {obj_a['name']} annotations are accurate?",
        ]
    else:
        return generate_questions_for_pair(obj_a, obj_b)

    selected = random.sample(pool, 3)
    return {"q1": selected[0], "q2": selected[1], "q3": selected[2]}

# =====================================================
# 📚 GENERAL VIDEO ANNOTATION QUESTIONS
# =====================================================
GENERAL_VIDEO_QUESTIONS = [
    {
        "title": "Temporal Interpolation",
        "description": "A client asks you to speed up the annotation process. They suggest using 'interpolation' for objects that move smoothly across frames.",
        "questions": [
            "Explain what temporal interpolation is in video annotation.",
            "When is it safe to use interpolation, and when should you avoid it?",
            "What happens to the bounding box if the object changes shape while moving (e.g., a person walking past a window)?",
            "If an object is occluded for 3 frames and reappears, how does interpolation handle that gap?"
        ]
    },
    {
        "title": "Tracking & ID Swapping",
        "description": "You are annotating a crowded scene with multiple pedestrians moving in different directions.",
        "questions": [
            "What visual features do you use to prevent ID swapping when two people cross paths?",
            "What is the protocol if you completely lose track of an object for more than 10 seconds?",
            "If a person leaves the frame and a different person enters wearing the exact same clothes, should they have the same tracking ID?",
            "How do you handle ID assignment for identical twins walking side-by-side?"
        ]
    },
    {
        "title": "Camera Movement",
        "description": "You are annotating footage shot by a drone that is panning, tilting, and moving forward simultaneously.",
        "questions": [
            "How does camera motion affect the tracking of stationary objects (e.g., trees, parked cars)?",
            "What is the difference between object motion and background motion in this scenario?",
            "How do you ensure the bounding boxes stay anchored to the objects as the camera pans?",
            "If the camera zooms in quickly, how should you resize the bounding boxes to keep them accurate?"
        ]
    },
    {
        "title": "Keyframes vs. Full Frame",
        "description": "A project manager asks you to annotate a 30-second clip of a car driving in a straight line.",
        "questions": [
            "What is the difference between a keyframe and a fully annotated frame?",
            "How often should you place keyframes on a smoothly moving object?",
            "What triggers the need for a new keyframe (e.g., scale change, occlusion, lighting)?",
            "Why is it bad practice to place only 1 keyframe at the start and 1 at the end of a video?"
        ]
    },
    {
        "title": "Occlusion Handling",
        "description": "An object in your video is heavily occluded by a tree for several frames.",
        "questions": [
            "If an object is completely hidden behind a tree for 5 frames, should you delete the bounding box, hide it, or leave it in place?",
            "What is the industry standard for annotating a person who is partially visible but their center is occluded?",
            "How do you maintain object tracking when the object's shape changes drastically due to occlusion?",
            "If the object never reappears in the video, what should the final state of the tracking ID be?"
        ]
    },
    {
        "title": "Bounding Box Jitter",
        "description": "You notice the bounding box around a parked car is jittering (shaking slightly) across 10 consecutive frames.",
        "questions": [
            "What causes bounding box jitter in video annotation?",
            "Why is a jittery bounding box bad for training a computer vision model?",
            "How can an annotator manually fix a jittery bounding box sequence?",
            "What tools do annotation platforms provide to smooth out bounding box movements?"
        ]
    },
    {
        "title": "Interpolation vs. Manual Tracking",
        "description": "The client asks why you manually annotated a fast-moving soccer ball instead of using automatic interpolation.",
        "questions": [
            "Explain why an object moving at high speed with motion blur might fail with automatic interpolation.",
            "When should an annotator completely ignore interpolation and rely solely on manual frame-by-frame labeling?",
            "If a ball spins rapidly in the air, how does that affect the accuracy of interpolation?",
            "What is the best way to validate that the interpolation engine tracked the ball correctly?"
        ]
    }
]

def build_batch_tasks_for_role(role):
    rng = random.Random(42)
    tasks = []
    
    if role == "image-annotator":
        num_tasks = INTERVIEW_CONFIG["task_count_image"]
    elif role == "video-annotator":
        num_tasks = INTERVIEW_CONFIG["task_count_video"]
    else:
        num_tasks = INTERVIEW_CONFIG["task_count_other"]
        
    for i in range(num_tasks):
        if role == "video-annotator":
            if i % 3 == 0: 
                gq = rng.choice(GENERAL_VIDEO_QUESTIONS)
                selected_questions = rng.sample(gq["questions"], 3)
                tasks.append({
                    "index": i, "task_type": "general_video", 
                    "title": gq["title"], "description": gq["description"],
                    "questions": {"q1": selected_questions[0], "q2": selected_questions[1], "q3": selected_questions[2]}
                })
            else:
                scenario = VIDEO_SCENARIOS_DB[i % len(VIDEO_SCENARIOS_DB)]
                selected_questions = rng.sample(scenario["questions"], 3)
                tasks.append({
                    "index": i, "task_type": "video", "title": scenario["title"],
                    "description": scenario["description"], "frames": scenario["frames"],
                    "questions": {"q1": selected_questions[0], "q2": selected_questions[1], "q3": selected_questions[2]}
                })
        elif role == "qa-reviewer":
            scenario = ANNOTATION_SCENARIOS_DB[i % len(ANNOTATION_SCENARIOS_DB)]
            selected_questions = rng.sample(scenario["questions"], 3)
            tasks.append({
                "index": i, "task_type": "qa", "title": scenario["title"],
                "description": scenario["description"], "qa_image": scenario["image"],
                "questions": {"q1": selected_questions[0], "q2": selected_questions[1], "q3": selected_questions[2]}
            })
        else:
            pair = rng.sample(OBJECTS_DB, 2)
            tasks.append({
                "index": i, "task_type": "standard",
                "object_a": pair[0], "object_b": pair[1],
                "image_a": get_random_image_for_object(pair[0]["name"], rng),
                "image_b": get_random_image_for_object(pair[1]["name"], rng),
                "questions": generate_questions_for_role(pair[0], pair[1], role)
            })
    return tasks

ROLE_BATCHES = {
    "image-annotator": build_batch_tasks_for_role("image-annotator"),
    "video-annotator": build_batch_tasks_for_role("video-annotator"),
    "qa-reviewer": build_batch_tasks_for_role("qa-reviewer"),
    "project-manager": build_batch_tasks_for_role("project-manager"),
}

# =====================================================
# 🔐 ACCESS CODE STORAGE & SESSIONS
# =====================================================
CODES_FILE = "access_codes.json"
SESSIONS_FILE = "sessions.json"

def load_codes():
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}
def save_codes(codes):
    with open(CODES_FILE, "w", encoding="utf-8") as f: json.dump(codes, f, indent=2)

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}
def save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f: json.dump(sessions, f, indent=2)

# =====================================================
# 📝 MODELS
# =====================================================
class StartSessionRequest(BaseModel):
    worker_name: str
    access_code: str
    role: str = "image-annotator"
    email: str = ""
    phone: str = ""

class SubmitAnswerRequest(BaseModel):
    session_id: str
    task_index: int
    answers: dict
    time_taken: int

class EndSessionRequest(BaseModel):
    session_id: str

class GenerateCodesRequest(BaseModel):
    count: int = 1
    assigned_to: str = ""

# =====================================================
# 🔐 ADMIN: ACCESS CODE MANAGEMENT
# =====================================================
@app.post("/admin/generate-codes")
def generate_codes(req: GenerateCodesRequest):
    if req.count < 1 or req.count > 100: raise HTTPException(400, "Count must be between 1 and 100")
    codes = load_codes()
    generated = []
    for _ in range(req.count):
        code = "ANNO-" + uuid.uuid4().hex[:8].upper()
        codes[code] = {
            "code": code, "assigned_to": req.assigned_to.strip(),
            "created_at": datetime.now().isoformat(), "status": "available",
            "used_by_session": None, "used_by_name": None, "used_at": None
        }
        generated.append(code)
    save_codes(codes)
    return {"generated": generated}

@app.get("/admin/codes")
def list_codes():
    codes = load_codes()
    return {"codes": sorted(codes.values(), key=lambda c: c["created_at"], reverse=True)}

@app.delete("/admin/codes/{code}")
def revoke_code(code: str):
    codes = load_codes()
    if code in codes:
        del codes[code]
        save_codes(codes)
        return {"status": "revoked", "code": code}
    raise HTTPException(404, "Code not found")

# =====================================================
# 🚪 START SESSION
# =====================================================
@app.post("/start-session")
def start_session(req: StartSessionRequest):
    code = req.access_code.strip().upper() 
    codes = load_codes()

    if code not in codes: raise HTTPException(403, "Invalid access code.")
    if codes[code]["status"] == "used": raise HTTPException(403, "This access code has already been used.")
    if not req.worker_name.strip(): raise HTTPException(400, "Name is required")

    session_id = "sess_" + uuid.uuid4().hex[:10]
    now = datetime.now()
    limit_seconds = INTERVIEW_CONFIG["time_limit_minutes"] * 60
    role = req.role if req.role in ROLE_BATCHES else "image-annotator"

    if role == "image-annotator":
        role_task_count = INTERVIEW_CONFIG["task_count_image"]
    elif role == "video-annotator":
        role_task_count = INTERVIEW_CONFIG["task_count_video"]
    else:
        role_task_count = INTERVIEW_CONFIG["task_count_other"]

    # 👇 SHUFFLE THE QUESTIONS FOR THIS SPECIFIC APPLICANT
    session_tasks = copy.deepcopy(ROLE_BATCHES[role])
    random.shuffle(session_tasks)
    
    # Re-index the tasks so the progress bar works correctly
    for idx, t in enumerate(session_tasks):
        t["index"] = idx

    sessions = load_sessions()
    sessions[session_id] = {
        "session_id": session_id, 
        "worker_name": req.worker_name.strip(), 
        "email": req.email,     
        "phone": req.phone,     
        "access_code": code,
        "role": role, 
        "started_at": now.isoformat(), 
        "expires_at": (now + timedelta(seconds=limit_seconds)).isoformat(),
        "time_limit": limit_seconds, 
        "task_count": role_task_count,
        "answers": [], 
        "status": "in_progress", 
        "completed_at": None,
        "tasks": session_tasks # 👈 Save the shuffled tasks to the session
    }
    save_sessions(sessions)

    codes[code]["status"] = "used"
    codes[code]["used_by_session"] = session_id
    codes[code]["used_by_name"] = req.worker_name.strip()
    codes[code]["used_at"] = now.isoformat()
    save_codes(codes)

    return {
        "session_id": session_id, "worker_name": req.worker_name, "role": role,
        "time_limit": limit_seconds, 
        "task_count": role_task_count, 
        "tasks": session_tasks, # 👈 Return the shuffled tasks
        "interview_name": INTERVIEW_CONFIG["interview_name"]
    }

# =====================================================
# 📝 SUBMIT ANSWER
# =====================================================
@app.post("/submit-answer")
def submit_answer(req: SubmitAnswerRequest):
    sessions = load_sessions()
    session = sessions.get(req.session_id)
    if not session: raise HTTPException(404, "Session not found")
    if datetime.now() > datetime.fromisoformat(session["expires_at"]): raise HTTPException(410, "Time limit exceeded")

    role = session.get("role", "image-annotator")
    
    # 👇 Read the task from the applicant's shuffled list
    task = session["tasks"][req.task_index] 
    
    task_type = task.get("task_type")
    if task_type == "video": task_info = f"Video: {task['title']}"
    elif task_type == "qa": task_info = f"QA: {task['title']}"
    elif task_type == "general_video": task_info = f"Theory: {task['title']}"
    else: task_info = f"{task['object_a']['name']} vs {task['object_b']['name']}"

    new_answer = {
        "task_index": req.task_index, "task_info": task_info,
        "q1": task["questions"]["q1"], "a1": req.answers.get("q1", ""),
        "q2": task["questions"]["q2"], "a2": req.answers.get("q2", ""),
        "q3": task["questions"]["q3"], "a3": req.answers.get("q3", ""),
        "time_taken": req.time_taken, "submitted_at": datetime.now().isoformat()
    }

    existing_idx = next((i for i, ans in enumerate(session["answers"]) if ans["task_index"] == req.task_index), None)
    if existing_idx is not None:
        session["answers"][existing_idx] = new_answer
    else:
        session["answers"].append(new_answer)

    if len(session["answers"]) >= session["task_count"]:
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()

    save_sessions(sessions)
    return {"status": "saved", "answered": len(session["answers"]), "total": session["task_count"]}

# =====================================================
# 📊 ADMIN STATS
# =====================================================
@app.get("/admin-stats")
def admin_stats():
    sessions = load_sessions()
    applicants = []
    for sid, s in sessions.items():
        completed = len(s.get("answers", []))
        completion_rate = round((completed / s["task_count"]) * 100) if s["task_count"] else 0
        total_time = sum(a.get("time_taken", 0) for a in s.get("answers", []))
        avg_time = round(total_time / completed, 1) if completed else 0
        applicants.append({
            "session_id": sid, 
            "worker_name": s["worker_name"], 
            "email": s.get("email", "N/A"),
            "phone": s.get("phone", "N/A"),
            "access_code": s.get("access_code", ""),
            "role": s.get("role", "image-annotator"), 
            "started_at": s["started_at"], 
            "status": s["status"],
            "tasks_completed": completed, 
            "task_count": s["task_count"],
            "completion_rate": completion_rate, 
            "avg_time_seconds": avg_time, 
            "score": completion_rate
        })
    applicants.sort(key=lambda x: (-x["score"], x["worker_name"]))
    return {"interview_name": INTERVIEW_CONFIG["interview_name"], "total_applicants": len(applicants), "applicants": applicants, "config": INTERVIEW_CONFIG}

@app.get("/admin/session/{session_id}")
def admin_session_detail(session_id: str):
    sessions = load_sessions()
    session = sessions.get(session_id)
    if not session: raise HTTPException(404, "Session not found")
    return session

@app.get("/admin/reset")
def admin_reset():
    save_sessions({})
    return {"status": "all sessions cleared"}

@app.get("/admin/reset-codes")
def admin_reset_codes():
    save_codes({})
    return {"status": "all codes cleared"}

# =====================================================
# 📈 ADMIN DASHBOARD HTML
# =====================================================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Interview Dashboard</title>
<style>
* { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }
body { background: #f4f6f9; padding: 40px; color: #2d3436; }
.wrap { max-width: 1400px; margin: 0 auto; }
h1 { margin-bottom: 8px; }
.subtitle { color: #636e72; margin-bottom: 30px; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
.card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
.card .label { color: #636e72; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }
.card .value { font-size: 2.2rem; font-weight: 700; color: #0984e3; margin-top: 8px; }
h2 { margin: 30px 0 15px; font-size: 1.3rem; display: flex; align-items: center; justify-content: space-between; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
th, td { padding: 14px 16px; text-align: left; border-bottom: 1px solid #ecf0f1; font-size: 0.9rem; }
th { background: #f8f9fa; font-weight: 600; color: #636e72; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 1px; }
tr:last-child td { border-bottom: 0; }
tr:hover { background: #f8f9fa; }
.badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }
.badge.completed { background: #d4edda; color: #155724; }
.badge.in_progress { background: #fff3cd; color: #856404; }
.badge.abandoned { background: #f8d7da; color: #721c24; }
.badge.expired { background: #e2e3e5; color: #383d41; }
.badge.available { background: #d1ecf1; color: #0c5460; }
.badge.used { background: #d4edda; color: #155724; }
.badge.revoked { background: #f8d7da; color: #721c24; }
.btn { background: #0984e3; color: white; border: none; padding: 10px 22px; border-radius: 30px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn:hover { background: #0873c7; }
.btn-green { background: #10b981; }
.btn-green:hover { background: #0e9f6e; }
.btn-small { padding: 6px 14px; font-size: 0.8rem; }
.btn-danger { background: #e74c3c; }
.btn-danger:hover { background: #c0392b; }
.code { font-family: monospace; background: #f1f3f5; padding: 4px 10px; border-radius: 6px; font-weight: 700; color: #2d3436; }
.actions-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
.actions-bar input { padding: 10px 14px; border: 1px solid #dfe6e9; border-radius: 8px; font-size: 0.9rem; }
.copy-btn { background: #dfe6e9; color: #2d3436; border: none; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; cursor: pointer; margin-left: 8px; }
.copy-btn:hover { background: #b2bec3; }
</style>
</head>
<body>
<div class="wrap">
    <h1>📈 Interview Dashboard</h1>
    <div class="subtitle" id="interview-name">Loading...</div>

    <div class="cards">
        <div class="card"><div class="label">Applicants</div><div class="value" id="total">-</div></div>
        <div class="card"><div class="label">Completed</div><div class="value" id="completed">-</div></div>
        <div class="card"><div class="label">Codes Available</div><div class="value" id="codes-avail">-</div></div>
        <div class="card"><div class="label">Time Limit</div><div class="value" id="config-val">-</div></div>
    </div>

    <h2>🔐 Access Codes</h2>
    <div class="actions-bar">
        <input type="text" id="assignee" placeholder="Assignee name (optional)" />
        <input type="number" id="code-count" value="1" min="1" max="100" style="width: 80px;" />
        <button class="btn btn-green" onclick="generateCodes()">+ Generate Codes</button>
        <button class="btn btn-danger btn-small" onclick="clearCodes()">Clear All Codes</button>
    </div>
    <table>
        <thead>
            <tr>
                <th>Code</th><th>Assigned To</th><th>Status</th>
                <th>Used By</th><th>Used At</th><th>Action</th>
            </tr>
        </thead>
        <tbody id="codes-table"></tbody>
    </table>

    <h2 style="margin-top: 50px;">📋 Applicants <button class="btn" onclick="load()" style="font-size:0.85rem; padding: 8px 18px;">🔄 Refresh</button></h2>
    <table>
        <thead>
            <tr>
                <th>#</th><th>Name</th><th>Contact Info</th><th>Role</th><th>Code</th><th>Status</th>
                <th>Tasks</th><th>Completion</th><th>Avg Time</th><th>Score</th><th>Started</th>
            </tr>
        </thead>
        <tbody id="applicants"></tbody>
    </table>
</div>

<script>
const ROLE_LABELS = {
    "image-annotator": "Image Annotator",
    "video-annotator": "Video Annotator",
    "qa-reviewer": "QA Reviewer",
    "project-manager": "Project Manager"
};

async function load() {
    const res = await fetch('/admin-stats');
    const data = await res.json();

    document.getElementById('interview-name').innerText = data.interview_name;
    document.getElementById('total').innerText = data.total_applicants;
    document.getElementById('completed').innerText = data.applicants.filter(a => a.status === 'completed').length;
    document.getElementById('config-val').innerText = data.config.time_limit_minutes + 'm';

    document.getElementById('applicants').innerHTML = data.applicants.map((a, i) => `
        <tr>
            <td>${i + 1}</td>
            <td><b>${a.worker_name}</b></td>
            <td><div style="font-size:0.8rem;">${a.email}</div><div style="font-size:0.8rem; color:#636e72;">${a.phone}</div></td>
            <td>${ROLE_LABELS[a.role] || a.role}</td>
            <td><span class="code">${a.access_code || '-'}</span></td>
            <td><span class="badge ${a.status}">${a.status.replace('_', ' ')}</span></td>
            <td>${a.tasks_completed} / ${a.task_count}</td>
            <td>${a.completion_rate}%</td>
            <td>${a.avg_time_seconds}s</td>
            <td><b style="color:#0984e3;">${a.score}</b></td>
            <td>${new Date(a.started_at).toLocaleString()}</td>
        </tr>
    `).join('') || '<tr><td colspan="11" style="text-align:center;color:#636e72;padding:30px;">No applicants yet.</td></tr>';

    const codesRes = await fetch('/admin/codes');
    const codesData = await codesRes.json();
    const avail = codesData.codes.filter(c => c.status === 'available').length;
    document.getElementById('codes-avail').innerText = avail;

    document.getElementById('codes-table').innerHTML = codesData.codes.map(c => `
        <tr>
            <td>
                <span class="code">${c.code}</span>
                <button class="copy-btn" onclick="navigator.clipboard.writeText('${c.code}'); this.innerText='Copied!'; setTimeout(()=>this.innerText='Copy', 1200);">Copy</button>
            </td>
            <td>${c.assigned_to || '<span style="color:#999;">—</span>'}</td>
            <td><span class="badge ${c.status}">${c.status}</span></td>
            <td>${c.used_by_name || '<span style="color:#999;">—</span>'}</td>
            <td>${c.used_at ? new Date(c.used_at).toLocaleString() : '<span style="color:#999;">—</span>'}</td>
            <td>${c.status === 'available' ? `<button class="btn btn-danger btn-small" onclick="revokeCode('${c.code}')">Revoke</button>` : '<span style="color:#999;">—</span>'}</td>
        </tr>
    `).join('') || '<tr><td colspan="6" style="text-align:center;color:#636e72;padding:30px;">No codes generated yet. Click "+ Generate Codes" above.</td></tr>';
}

async function generateCodes() {
    const count = parseInt(document.getElementById('code-count').value) || 1;
    const assigned = document.getElementById('assignee').value.trim();
    const res = await fetch('/admin/generate-codes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count, assigned_to: assigned })
    });
    const data = await res.json();
    alert('Generated ' + data.generated.length + ' code(s):\\n\\n' + data.generated.join('\\n'));
    document.getElementById('assignee').value = '';
    load();
}

async function revokeCode(code) {
    if (!confirm('Revoke code ' + code + '?')) return;
    await fetch('/admin/codes/' + code, { method: 'DELETE' });
    load();
}

async function clearCodes() {
    if (!confirm('Delete ALL access codes? This cannot be undone.')) return;
    await fetch('/admin/reset-codes');
    load();
}

load();
setInterval(load, 15000);
</script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    return ADMIN_HTML

# =====================================================
# 📄 DOCUMENT UPLOADS (W-9 & ID)
# =====================================================
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

@app.post("/upload-documents")
async def upload_documents(
    session_id: str = Form(...),
    id_front: UploadFile = File(None),
    id_back: UploadFile = File(None),
    w9_doc: UploadFile = File(None)
):
    sessions = load_sessions()
    session = sessions.get(session_id)
    if not session: raise HTTPException(404, "Session not found")

    saved_files = []
    
    async def save_file(file: UploadFile, prefix: str):
        if file and file.filename:
            filename = f"{session_id}_{prefix}_{file.filename}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return filename
        return None

    f1 = await save_file(id_front, "id_front")
    f2 = await save_file(id_back, "id_back")
    f3 = await save_file(w9_doc, "w9")
    
    session["documents"] = {"id_front": f1, "id_back": f2, "w9": f3}
    save_sessions(sessions)
    
    return {"status": "success", "documents": session["documents"]}

# =====================================================
# 🌐 MOUNT STATIC FOLDERS
# =====================================================
BASE_DIR = Path(__file__).resolve().parent

@app.get("/website/index.html")
def serve_homepage():
    return FileResponse(BASE_DIR / "website" / "index.html")

app.mount("/website", StaticFiles(directory=BASE_DIR / "website", html=True), name="website")
app.mount("/interview", StaticFiles(directory=BASE_DIR / "interview", html=True), name="interview")

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/website/index.html")